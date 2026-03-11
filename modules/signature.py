# signature.py - ECDSA P-256 key generation, signing and verification
# done by sumanth

import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

KEYS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "keys")


def generate_keys(key_dir: str = None) -> None:
    if key_dir is None:
        key_dir = KEYS_DIR
    os.makedirs(key_dir, exist_ok=True)

    private_key = ec.generate_private_key(ec.SECP256R1())

    # save private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_key_path = os.path.join(key_dir, "private_key.pem")
    with open(private_key_path, "wb") as f:
        f.write(private_pem)

    # save public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_key_path = os.path.join(key_dir, "public_key.pem")
    with open(public_key_path, "wb") as f:
        f.write(public_pem)

    print(f"  [+] ECDSA P-256 keys generated")
    print(f"      Private: {private_key_path}")
    print(f"      Public:  {public_key_path}")


def load_private_key(key_path: str = None):
    if key_path is None:
        key_path = os.path.join(KEYS_DIR, "private_key.pem")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Private key not found: {key_path}\nRun 'python main.py genkeys' first.")
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key(key_path: str = None):
    if key_path is None:
        key_path = os.path.join(KEYS_DIR, "public_key.pem")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Public key not found: {key_path}\nRun 'python main.py genkeys' first.")
    with open(key_path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def sign_hash(private_key, hash_value: str) -> bytes:
    # signs the hash using ECDSA with SHA-256
    hash_bytes = hash_value.encode("utf-8")
    return private_key.sign(hash_bytes, ec.ECDSA(hashes.SHA256()))


def verify_signature(public_key, hash_value: str, signature: bytes) -> bool:
    # checks if signature matches the hash
    hash_bytes = hash_value.encode("utf-8")
    try:
        public_key.verify(signature, hash_bytes, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False
