# verification.py - image authenticity verification pipeline
# done by sahasra

import numpy as np
import cv2
from modules.image_io import load_image
from modules.signature import load_public_key, verify_signature
from modules.embedding import extract_signature_dct


def compute_robust_hash(image: np.ndarray, grid_size: int = 16) -> str:
    # block-mean perceptual hash - stable across compression but detects edits
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    h, w = gray.shape
    block_h = h // grid_size
    block_w = w // grid_size

    # compute mean intensity per block
    means = []
    for r in range(grid_size):
        for c in range(grid_size):
            block = gray[r * block_h:(r + 1) * block_h,
                         c * block_w:(c + 1) * block_w]
            means.append(float(block.mean()))

    means = np.array(means)
    median_val = np.median(means)

    # threshold against median to get binary hash
    hash_bits = (means > median_val).astype(np.uint8)
    bit_string = "".join(str(b) for b in hash_bits)

    while len(bit_string) % 8 != 0:
        bit_string += "0"

    hash_bytes = int(bit_string, 2).to_bytes(len(bit_string) // 8, byteorder="big")
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
