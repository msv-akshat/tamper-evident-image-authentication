#!/usr/bin/env python3
# test_scenario.py - basic sign/verify/tamper test

import os
import sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.image_io import load_image, save_image
from modules.signature import generate_keys, load_private_key, sign_hash
from modules.embedding import embed_signature_dct
from modules.verification import verify_image, compute_robust_hash


def create_test_image(path, width=256, height=256):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            img[y, x] = [(x + y) % 256, (x * 2) % 256, (y * 2) % 256]
    cv2.imwrite(path, img)
    print(f"  Created: {path} ({width}x{height})")


def run_test():
    print("=" * 50)
    print("  IMAGE AUTH - TEST SCENARIO")
    print("=" * 50)

    os.makedirs("keys", exist_ok=True)
    os.makedirs("test_images", exist_ok=True)
    os.makedirs("signed_images", exist_ok=True)

    test_img = os.path.join("test_images", "test_gradient.png")
    signed_img = os.path.join("signed_images", "test_signed.png")
    tampered_img = os.path.join("test_images", "test_tampered.png")

    # generate keys
    print("\n[1] Generating keys...")
    generate_keys()

    # create test image
    print("\n[2] Creating test image...")
    create_test_image(test_img)

    # sign image
    print("\n[3] Signing image...")
    image = load_image(test_img)
    image_hash = compute_robust_hash(image)
    print(f"  Hash: {image_hash[:32]}...")

    private_key = load_private_key()
    signature = sign_hash(private_key, image_hash)
    print(f"  Signature: {len(signature)} bytes")

    signed_image = embed_signature_dct(image, signature)
    save_image(signed_img, signed_image)

    # verify (should be authentic)
    print("\n[4] Verifying signed image...")
    result = verify_image(signed_img)
    print(f"  Result: {result}")
    assert result == "AUTHENTIC", f"Expected AUTHENTIC, got {result}"
    print("  PASS")

    # tamper with the image
    print("\n[5] Tampering with image...")
    tampered = load_image(signed_img)
    h, w = tampered.shape[:2]
    tampered[h//4:h//2, w//4:w//2] = [255, 0, 0]
    save_image(tampered_img, tampered)

    # verify tampered (should be tampered)
    print("\n[6] Verifying tampered image...")
    result = verify_image(tampered_img)
    print(f"  Result: {result}")
    assert result == "TAMPERED", f"Expected TAMPERED, got {result}"
    print("  PASS")

    print("\n" + "=" * 50)
    print("  ALL TESTS PASSED")
    print("=" * 50)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_test()
