import base64
import hashlib
import os
import sys
from typing import Any, Dict, List

import cv2
import numpy as np

# Ensure existing project modules are importable from backend/app/services.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.embedding import embed_signature_dct, extract_signature_dct
from modules.embedding import EMBED_POSITIONS, EMBED_STRENGTH, HEADER_BITS, signature_to_binary
from modules.signature import generate_keys, load_private_key, load_public_key, sign_hash, verify_signature
from modules.verification import compute_robust_hash


# WhatsApp commonly downsizes large images before heavy JPEG compression.
# Keeping signed outputs under this side length avoids resize-induced extraction failure.
MAX_SIGN_DIMENSION = 1600


def _ensure_keys() -> None:
    private_key_path = os.path.join(PROJECT_ROOT, "keys", "private_key.pem")
    public_key_path = os.path.join(PROJECT_ROOT, "keys", "public_key.pem")
    if not os.path.exists(private_key_path) or not os.path.exists(public_key_path):
        generate_keys()


def _decode_image(image_bytes: bytes) -> np.ndarray:
    np_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image file")
    return image


def _encode_png_base64(image: np.ndarray) -> str:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Failed to encode signed image")
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _signature_preview(signature_b64: str, preview_chars: int = 50) -> str:
    if len(signature_b64) <= preview_chars:
        return signature_b64
    return signature_b64[:preview_chars]


def _normalize_image_for_sharing(image: np.ndarray) -> tuple[np.ndarray, Dict[str, int]]:
    h, w = image.shape[:2]
    max_dim = max(h, w)
    if max_dim <= MAX_SIGN_DIMENSION:
        return image, {"width": int(w), "height": int(h), "resized": 0}

    scale = MAX_SIGN_DIMENSION / float(max_dim)
    new_w = max(8, int(round(w * scale)))
    new_h = max(8, int(round(h * scale)))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, {"width": int(new_w), "height": int(new_h), "resized": 1}


def _build_embedding_debug(image: np.ndarray, signature_bytes: bytes) -> Dict[str, Any]:
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y_channel = ycrcb[:, :, 0].astype(np.float32)
    h, w = y_channel.shape

    block_rows = h // 8
    block_cols = w // 8
    payload = format(len(signature_bytes), "032b") + signature_to_binary(signature_bytes)

    all_operations: List[Dict[str, Any]] = []
    selected_block_before = None
    selected_block_after = None
    selected_dct_before = None
    selected_dct_after = None
    selected_delta = None
    selected_block_meta = None
    selected_block_operations: List[Dict[str, Any]] = []
    best_change_score = -1.0

    bit_index = 0
    block_index = 0
    for r in range(0, h - 7, 8):
        for c in range(0, w - 7, 8):
            if bit_index >= len(payload):
                break

            block_original = y_channel[r:r + 8, c:c + 8].astype(np.float32)
            block_working = block_original.copy()
            block_ops: List[Dict[str, Any]] = []
            modified_in_block = False

            for pos in EMBED_POSITIONS:
                if bit_index >= len(payload):
                    break

                bit = int(payload[bit_index])
                dct_block = cv2.dct(block_working)
                coeff_before = float(dct_block[pos[0], pos[1]])

                q_index_before = round(coeff_before / EMBED_STRENGTH)
                q_index_after = q_index_before

                if (q_index_after % 2) != bit:
                    if abs(coeff_before - (q_index_after + 1) * EMBED_STRENGTH) < abs(
                        coeff_before - (q_index_after - 1) * EMBED_STRENGTH
                    ):
                        q_index_after += 1
                    else:
                        q_index_after -= 1

                coeff_after = float(q_index_after * EMBED_STRENGTH)
                dct_block[pos[0], pos[1]] = coeff_after
                block_working = cv2.idct(dct_block)

                was_modified = abs(coeff_after - coeff_before) > 1e-6
                if was_modified:
                    modified_in_block = True

                operation = {
                    "payload_bit_index": bit_index,
                    "block_index": block_index,
                    "block_row": r // 8,
                    "block_col": c // 8,
                    "dct_position": [pos[0], pos[1]],
                    "embedded_bit": bit,
                    "coeff_before": round(coeff_before, 4),
                    "coeff_after": round(coeff_after, 4),
                    "coeff_delta": round(coeff_after - coeff_before, 4),
                    "q_index_before": int(q_index_before),
                    "q_index_after": int(q_index_after),
                    "was_modified": was_modified,
                }
                block_ops.append(operation)
                all_operations.append(operation)

                bit_index += 1

            # Select the block with the strongest pixel-domain embedding impact.
            block_delta = block_working - block_original
            change_score = float(np.max(np.abs(block_delta)))
            if change_score > best_change_score:
                best_change_score = change_score
                selected_block_before = np.round(block_original, 4).tolist()
                selected_block_after = np.round(block_working, 4).tolist()
                selected_delta = np.round(block_delta, 6).tolist()

                dct_before = cv2.dct(block_original)
                dct_after = cv2.dct(block_working)
                selected_dct_before = np.round(dct_before, 4).tolist()
                selected_dct_after = np.round(dct_after, 4).tolist()

                selected_block_meta = {
                    "block_row": r // 8,
                    "block_col": c // 8,
                    "block_index": block_index,
                    "block_variance": round(float(np.var(block_original)), 4),
                    "max_abs_pixel_delta": round(change_score, 6),
                    "modified_in_block": modified_in_block,
                }
                selected_block_operations = [dict(op) for op in block_ops]

            block_index += 1

        if bit_index >= len(payload):
            break

    modified_ops = [op for op in all_operations if op["was_modified"]]
    selected_block_modified_ops = [op for op in selected_block_operations if op["was_modified"]]

    # Build a clearer sample: include both embedded 0-bits and 1-bits when possible.
    zero_bit_ops = [op for op in modified_ops if op["embedded_bit"] == 0]
    one_bit_ops = [op for op in modified_ops if op["embedded_bit"] == 1]

    sample_operations = zero_bit_ops[:4] + one_bit_ops[:4]
    used_indices = {op["payload_bit_index"] for op in sample_operations}

    if len(sample_operations) < 8:
        for op in modified_ops:
            if op["payload_bit_index"] not in used_indices:
                sample_operations.append(op)
                used_indices.add(op["payload_bit_index"])
            if len(sample_operations) >= 8:
                break

    if len(sample_operations) < 8:
        for op in all_operations:
            if op["payload_bit_index"] not in used_indices:
                sample_operations.append(op)
                used_indices.add(op["payload_bit_index"])
            if len(sample_operations) >= 8:
                break

    return {
        "block_size": 8,
        "image_size": {"width": int(w), "height": int(h)},
        "block_grid": {"rows": int(block_rows), "cols": int(block_cols)},
        "header_bits": HEADER_BITS,
        "payload_bit_count": int(len(payload)),
        "payload_preview": payload[:96],
        "dct_positions": [[r, c] for r, c in EMBED_POSITIONS],
        "quantization_step": EMBED_STRENGTH,
        "selected_block_meta": selected_block_meta,
        "selected_block_before": selected_block_before,
        "selected_block_after": selected_block_after,
        "selected_block_delta": selected_delta,
        "selected_dct_before": selected_dct_before,
        "selected_dct_after": selected_dct_after,
        "selected_block_operations": selected_block_operations,
        "selected_block_modified_operations_count": len(selected_block_modified_ops),
        "selected_block_total_operations": len(selected_block_operations),
        "selected_block_explanation": {
            "block_row": int(selected_block_meta["block_row"]) if selected_block_meta else None,
            "block_col": int(selected_block_meta["block_col"]) if selected_block_meta else None,
            "grid_rows": int(block_rows),
            "grid_cols": int(block_cols),
        },
        "modified_operations_count": len(modified_ops),
        "total_operations_scanned": len(all_operations),
        # Kept for backward compatibility with existing UI paths.
        "sample_operations": sample_operations,
    }


def sign_image_bytes(image_bytes: bytes) -> Dict[str, Any]:
    debug_steps: List[str] = []

    image = _decode_image(image_bytes)
    debug_steps.append("Image loaded")

    image, normalization_info = _normalize_image_for_sharing(image)
    if normalization_info["resized"]:
        debug_steps.append(
            f"Resized before signing for share robustness: {normalization_info['width']}x{normalization_info['height']}"
        )
    else:
        debug_steps.append("Input size already share-safe; no resize needed")

    robust_hash = compute_robust_hash(image)
    final_hash = _sha256_hex(robust_hash)
    debug_steps.append("Hash generated")

    _ensure_keys()
    private_key = load_private_key()
    signature_bytes = sign_hash(private_key, final_hash)
    signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")
    debug_steps.append("Signature created")

    embedding_debug = _build_embedding_debug(image, signature_bytes)
    debug_steps.append("Prepared DCT intermediate debug data")

    signed_image = embed_signature_dct(image, signature_bytes)
    signed_image_b64 = _encode_png_base64(signed_image)
    debug_steps.append("Signature embedded")

    return {
        "hash": final_hash,
        "signature": signature_b64,
        "signature_preview": _signature_preview(signature_b64),
        "embedding_info": {
            "method": "DCT",
            "description": "Signature embedded into frequency domain",
        },
        "normalization": normalization_info,
        "embedding_debug": embedding_debug,
        "signed_image": signed_image_b64,
        "debug_steps": debug_steps,
    }


def verify_image_bytes(image_bytes: bytes) -> Dict[str, Any]:
    image = _decode_image(image_bytes)

    try:
        extracted_signature_bytes = extract_signature_dct(image)
        extracted_signature_b64 = base64.b64encode(extracted_signature_bytes).decode("utf-8")
    except ValueError:
        extracted_signature_bytes = b""
        extracted_signature_b64 = ""

    robust_hash = compute_robust_hash(image)
    recomputed_hash = _sha256_hex(robust_hash)

    _ensure_keys()
    public_key = load_public_key()

    is_valid = False
    if extracted_signature_bytes:
        is_valid = verify_signature(public_key, recomputed_hash, extracted_signature_bytes)

    comparison_details = {
        "algorithm": "ECDSA P-256 verify with SHA-256 hashed image fingerprint",
        "comparison_rule": "is_valid = verify(public_key, recomputed_hash, extracted_signature)",
        "recomputed_hash_length": len(recomputed_hash),
        "extracted_signature_length_bytes": len(extracted_signature_bytes),
        "checks": [
            "1) Extract signature bytes from DCT-embedded coefficients.",
            "2) Recompute image fingerprint and hash it with SHA-256.",
            "3) Verify extracted signature against recomputed hash using public key.",
        ],
        "result": "signature matches recomputed hash" if is_valid else "signature does not match recomputed hash",
    }

    return {
        "extracted_signature": extracted_signature_b64,
        "recomputed_hash": recomputed_hash,
        "is_valid": is_valid,
        "message": "Authentic" if is_valid else "Tampered",
        "comparison_details": comparison_details,
    }
