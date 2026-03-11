# embedding.py - DCT domain steganography for embedding/extracting signatures
# done by akshat

import numpy as np
import cv2

# config
HEADER_BITS = 32
EMBED_POSITIONS = [(3, 2), (2, 3), (4, 1), (1, 4)]  # mid-freq DCT positions
EMBED_STRENGTH = 35.0  # quantization step (higher = more robust to compression)
MIN_REDUNDANCY = 7


def signature_to_binary(signature_bytes: bytes) -> str:
    return "".join(format(byte, "08b") for byte in signature_bytes)


def binary_to_signature(binary_str: str) -> bytes:
    return bytes(int(binary_str[i:i+8], 2) for i in range(0, len(binary_str), 8))


def _to_ycrcb(image: np.ndarray):
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    return ycrcb, ycrcb[:, :, 0].astype(np.float32)


def _from_ycrcb(ycrcb: np.ndarray, y_channel: np.ndarray) -> np.ndarray:
    ycrcb = ycrcb.copy()
    ycrcb[:, :, 0] = np.clip(y_channel, 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)


def _get_blocks(y_channel: np.ndarray):
    # yields top-left corner of every 8x8 block
    h, w = y_channel.shape
    for r in range(0, h - 7, 8):
        for c in range(0, w - 7, 8):
            yield r, c


def _embed_bit_in_block(block: np.ndarray, bit: int, pos: tuple) -> np.ndarray:
    # QIM embedding - quantize DCT coeff to encode bit via parity
    dct_block = cv2.dct(block.astype(np.float32))
    coeff = dct_block[pos[0], pos[1]]
    q = EMBED_STRENGTH
    qi = round(coeff / q)

    if (qi % 2) != bit:
        if abs(coeff - (qi + 1) * q) < abs(coeff - (qi - 1) * q):
            qi += 1
        else:
            qi -= 1

    dct_block[pos[0], pos[1]] = qi * q
    return cv2.idct(dct_block)


def _extract_bit_from_block(block: np.ndarray, pos: tuple) -> int:
    # QIM decoding - read parity of quantized DCT coeff
    dct_block = cv2.dct(block.astype(np.float32))
    coeff = dct_block[pos[0], pos[1]]
    return int(round(coeff / EMBED_STRENGTH) % 2)


def embed_signature_dct(image: np.ndarray, signature_bytes: bytes) -> np.ndarray:
    sig_binary = signature_to_binary(signature_bytes)
    sig_length = len(signature_bytes)

    # payload = 32-bit header (sig length) + signature bits
    payload = format(sig_length, "032b") + sig_binary
    total_payload_bits = len(payload)

    ycrcb, y_channel = _to_ycrcb(image)
    blocks = list(_get_blocks(y_channel))
    total_slots = len(blocks) * len(EMBED_POSITIONS)

    if total_slots < total_payload_bits:
        raise ValueError(f"Image too small. Need {total_payload_bits} slots, have {total_slots}.")

    # cap redundancy so we dont embed into too many blocks
    redundancy = max(1, total_slots // total_payload_bits)
    redundancy = min(redundancy, MIN_REDUNDANCY * 3)

    print(f"    Embedding: {total_payload_bits} bits, {len(blocks)} blocks, "
          f"{total_slots} slots, {redundancy}x redundancy")

    full_bitstream = (payload * redundancy)[:total_slots]

    # embed bits into DCT coefficients of each block
    modified_y = y_channel.copy()
    bit_idx = 0
    for r, c in blocks:
        block = modified_y[r:r+8, c:c+8].copy()
        for pos in EMBED_POSITIONS:
            if bit_idx >= len(full_bitstream):
                break
            block = _embed_bit_in_block(block, int(full_bitstream[bit_idx]), pos)
            bit_idx += 1
        modified_y[r:r+8, c:c+8] = block
        if bit_idx >= len(full_bitstream):
            break

    return _from_ycrcb(ycrcb, modified_y)


def extract_signature_dct(image: np.ndarray) -> bytes:
    _, y_channel = _to_ycrcb(image)
    blocks = list(_get_blocks(y_channel))
    total_slots = len(blocks) * len(EMBED_POSITIONS)

    # read all bits from the image
    raw_bits = []
    for r, c in blocks:
        block = y_channel[r:r+8, c:c+8].astype(np.float32)
        for pos in EMBED_POSITIONS:
            raw_bits.append(_extract_bit_from_block(block, pos))

    print(f"    Extracting: {len(blocks)} blocks, {total_slots} slots")

    if len(raw_bits) < HEADER_BITS:
        raise ValueError("Image too small to contain a signature header.")

    # read header from first copy to get sig length
    raw_header_val = int("".join(str(raw_bits[i]) for i in range(HEADER_BITS)), 2)
    print(f"    Raw header: {raw_header_val} bytes")

    # try raw header first, then fallback to common ECDSA sizes
    candidates = []
    if 1 <= raw_header_val <= 512:
        candidates.append(raw_header_val)
    for size in [70, 71, 72, 73, 80]:
        if size not in candidates:
            candidates.append(size)

    # for each candidate, do majority voting with capped redundancy
    for candidate_len in candidates:
        payload_size = HEADER_BITS + (candidate_len * 8)
        if payload_size > total_slots:
            continue

        # must match the cap used during embedding
        redundancy = min(total_slots // payload_size, MIN_REDUNDANCY * 3)
        if redundancy < 1:
            redundancy = 1
        embedded_bit_count = payload_size * redundancy

        # majority vote across redundant copies
        voted_payload = []
        for bit_pos in range(payload_size):
            ones = 0
            count = 0
            for copy_idx in range(redundancy):
                idx = copy_idx * payload_size + bit_pos
                if idx < embedded_bit_count and idx < len(raw_bits):
                    ones += raw_bits[idx]
                    count += 1
            voted_payload.append(1 if count > 0 and ones > count / 2 else 0)

        # validate: voted header should match candidate
        voted_header = int("".join(str(b) for b in voted_payload[:HEADER_BITS]), 2)

        if voted_header == candidate_len:
            sig_bits = voted_payload[HEADER_BITS:HEADER_BITS + voted_header * 8]
            if len(sig_bits) == voted_header * 8:
                sig_bytes = binary_to_signature("".join(str(b) for b in sig_bits))
                print(f"    Extracted: {voted_header}-byte signature ({redundancy}x redundancy)")
                return sig_bytes

    raise ValueError(f"Could not recover signature. Raw header={raw_header_val}.")


# legacy wrappers
def embed_signature(image, signature_bytes):
    return embed_signature_dct(image, signature_bytes)

def extract_signature(image):
    return extract_signature_dct(image)
