# hashing.py - SHA-256 hash of image pixel data
# done by sumanth

import hashlib
import numpy as np


def generate_image_hash(pixel_array: np.ndarray) -> str:
    # converts pixel data to bytes and returns sha256 hex digest
    pixel_bytes = pixel_array.tobytes()
    return hashlib.sha256(pixel_bytes).hexdigest()
