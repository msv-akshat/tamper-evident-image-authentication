#!/usr/bin/env python3
# main.py - CLI for tamper-evident image authentication system
#
# usage:
#   python main.py genkeys                     - generate ECDSA key pair
#   python main.py sign <input> <output.png>   - sign an image
#   python main.py verify <signed.png>         - verify a signed image

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.image_io import load_image, save_image
from modules.signature import generate_keys, load_private_key, sign_hash
from modules.embedding import embed_signature_dct
from modules.verification import verify_image, compute_robust_hash


def cmd_genkeys(args):
    print("\n  Generating ECDSA P-256 key pair...")
    key_dir = args.keydir if args.keydir else None
    generate_keys(key_dir)
    print("  Done.\n")


def cmd_sign(args):
    input_path = args.input
    output_path = args.output

    if not output_path.lower().endswith(".png"):
        print("  [!] Output should be .png for lossless storage. Appending .png")
        output_path += ".png"

    print(f"\n  Loading: {input_path}")
    image = load_image(input_path)
    h, w, c = image.shape
    print(f"    Size: {w}x{h}, {c} channels")

    # compute perceptual hash
    print("  Computing perceptual hash...")
    image_hash = compute_robust_hash(image)
    print(f"    Hash: {image_hash[:32]}...")

    # sign the hash
    print("  Signing with ECDSA...")
    private_key = load_private_key(args.keyfile if args.keyfile else None)
    signature = sign_hash(private_key, image_hash)
    print(f"    Signature: {len(signature)} bytes")

    # embed into image
    print("  Embedding signature (DCT)...")
    signed_image = embed_signature_dct(image, signature)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    save_image(output_path, signed_image)
    print(f"  Saved: {output_path}\n")


def cmd_verify(args):
    image_path = args.image
    public_key_path = args.keyfile if args.keyfile else None

    print(f"\n  Verifying: {image_path}")
    result = verify_image(image_path, public_key_path)

    print(f"\n  {'=' * 40}")
    print(f"   Result: {result}")
    print(f"  {'=' * 40}\n")

    return 0 if result == "AUTHENTIC" else 1


def main():
    parser = argparse.ArgumentParser(
        description="Tamper-Evident Image Authentication System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python main.py genkeys
  python main.py sign input.jpg signed_images/output.png
  python main.py verify signed_images/output.png
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="available commands")

    # genkeys
    gk = subparsers.add_parser("genkeys", help="Generate ECDSA P-256 key pair")
    gk.add_argument("--keydir", type=str, default=None, help="Key directory (default: keys/)")

    # sign
    sp = subparsers.add_parser("sign", help="Sign an image")
    sp.add_argument("input", type=str, help="Input image path")
    sp.add_argument("output", type=str, help="Output signed image (.png)")
    sp.add_argument("--keyfile", type=str, default=None, help="Private key path")

    # verify
    vp = subparsers.add_parser("verify", help="Verify a signed image")
    vp.add_argument("image", type=str, help="Signed image path")
    vp.add_argument("--keyfile", type=str, default=None, help="Public key path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "genkeys":
            cmd_genkeys(args)
        elif args.command == "sign":
            cmd_sign(args)
        elif args.command == "verify":
            sys.exit(cmd_verify(args))
    except (FileNotFoundError, ValueError) as e:
        print(f"\n  [ERROR] {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
