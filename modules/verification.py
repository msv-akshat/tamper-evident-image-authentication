# verification.py - image authenticity verification pipeline
# done by sahasra

import numpy as np
import cv2
from modules.image_io import load_image
from modules.signature import load_public_key, verify_signature
from modules.embedding import extract_signature_dct


def compute_robust_hash(image: np.ndarray, grid_size: int = 16) -> str:
    # Coarse low-frequency DCT hash. It is intentionally quantized so small
    # embedding/compression perturbations do not flip the signed message.
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Keep deterministic dimensions regardless of source resolution.
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    smoothed = cv2.GaussianBlur(resized, (5, 5), 0)

    dct_block = cv2.dct(smoothed.astype(np.float32))
    low_freq = dct_block[:4, :4].flatten()[1:]  # drop DC term

    quant_step = 30.0
    quantized = np.round(low_freq / quant_step).astype(np.int16)
    quantized = np.clip(quantized, -128, 127)

    # Encode signed bins into bytes so the hash string remains compact and stable.
    hash_bytes = (quantized + 128).astype(np.uint8).tobytes()
    return hash_bytes.hex()


def verify_image(image_path: str, public_key_path: str = None) -> str:
    # load image -> extract signature -> compute hash -> verify
    signed_image = load_image(image_path)

    try:
        extracted_signature = extract_signature_dct(signed_image)
    except ValueError as e:
        print(f"  [!] Extraction failed: {e}")
        return "TAMPERED"

    recomputed_hash = compute_robust_hash(signed_image)
    public_key = load_public_key(public_key_path)
    is_valid = verify_signature(public_key, recomputed_hash, extracted_signature)

    return "AUTHENTIC" if is_valid else "TAMPERED"
