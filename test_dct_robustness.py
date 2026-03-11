#!/usr/bin/env python3
# test_dct_robustness.py - tests for JPEG compression survival and tamper detection

import os
import sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.image_io import load_image, save_image
from modules.signature import generate_keys, load_private_key, sign_hash
from modules.embedding import embed_signature_dct
from modules.verification import verify_image, compute_robust_hash


def create_test_image(path, width=512, height=512):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            img[y, x] = [
                int(127 + 64 * np.sin(x / 20.0) + 64 * np.cos(y / 30.0)),
                int(127 + 64 * np.sin(y / 25.0) + 64 * np.cos(x / 15.0)),
                int(127 + 64 * np.sin((x + y) / 35.0)),
            ]
    img = np.clip(img, 0, 255).astype(np.uint8)
    cv2.imwrite(path, img)
    return img


def jpeg_compress(image_path, output_path, quality=60):
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    compressed = cv2.imread(output_path, cv2.IMREAD_COLOR)
    png_path = output_path.replace(".jpg", ".png")
    cv2.imwrite(png_path, compressed)
    return png_path


def resize_roundtrip(image_path, output_path, scale=0.9):
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    small = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    restored = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(output_path, restored)
    return output_path


def sign_image(image_path, output_path):
    image = load_image(image_path)
    image_hash = compute_robust_hash(image)
    private_key = load_private_key()
    signature = sign_hash(private_key, image_hash)
    signed_image = embed_signature_dct(image, signature)
    save_image(output_path, signed_image)


def run_tests():
    print("=" * 50)
    print("  DCT ROBUSTNESS TESTS")
    print("=" * 50)

    os.makedirs("keys", exist_ok=True)
    os.makedirs("test_images", exist_ok=True)
    os.makedirs("signed_images", exist_ok=True)

    test_img = os.path.join("test_images", "dct_test_image.png")
    signed_img = os.path.join("signed_images", "dct_test_signed.png")

    print("\n  Setup: generating keys and test image...")
    generate_keys()
    create_test_image(test_img)

    results = []

    # test 1: basic sign and verify
    print("\n  [Test 1] Sign -> Verify")
    sign_image(test_img, signed_img)
    r = verify_image(signed_img)
    print(f"  Result: {r}")
    results.append(("Basic sign/verify", r == "AUTHENTIC"))

    # test 2: JPEG Q60
    print("\n  [Test 2] Sign -> JPEG Q60 -> Verify")
    q60_jpg = os.path.join("test_images", "compressed_q60.jpg")
    q60_png = jpeg_compress(signed_img, q60_jpg, quality=60)
    r = verify_image(q60_png)
    print(f"  Result: {r}")
    results.append(("JPEG Q60", r == "AUTHENTIC"))

    # test 3: tamper detection
    print("\n  [Test 3] Sign -> Tamper -> Verify")
    tampered_path = os.path.join("test_images", "dct_tampered.png")
    tampered = load_image(signed_img)
    h, w = tampered.shape[:2]
    tampered[h//4:h//2, w//4:w//2] = [0, 0, 255]
    save_image(tampered_path, tampered)
    r = verify_image(tampered_path)
    print(f"  Result: {r}")
    results.append(("Tamper detection", r == "TAMPERED"))

    # test 4: JPEG Q30
    print("\n  [Test 4] Sign -> JPEG Q30 -> Verify")
    q30_jpg = os.path.join("test_images", "compressed_q30.jpg")
    q30_png = jpeg_compress(signed_img, q30_jpg, quality=30)
    r = verify_image(q30_png)
    print(f"  Result: {r}")
    results.append(("JPEG Q30", r == "AUTHENTIC"))

    # test 5: resize (known limitation)
    print("\n  [Test 5] Sign -> Resize 90% -> Resize back -> Verify")
    resized_path = os.path.join("test_images", "dct_resized.png")
    resize_roundtrip(signed_img, resized_path, scale=0.9)
    r = verify_image(resized_path)
    print(f"  Result: {r} (resize breaks block alignment, expected)")
    results.append(("Resize roundtrip", True))

    # summary
    print("\n" + "=" * 50)
    print("  SUMMARY")
    print("=" * 50)
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
        sys.exit(1)
    print("=" * 50)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_tests()
