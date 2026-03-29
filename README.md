# Tamper-Evident Image Authentication Using Embedded Cryptographic Signatures

A Python-based system that digitally signs images by embedding an ECDSA cryptographic signature into the DCT (Discrete Cosine Transform) domain of the image. On verification, the signature is extracted and validated to determine whether the image is **authentic** or has been **tampered with**.

The DCT-domain embedding (QIM — Quantization Index Modulation) makes the signature robust against JPEG compression and mild image transformations, unlike basic LSB steganography.

---

## Architecture

### Signing Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌──────────┐     ┌───────────┐     ┌──────────────┐
│ Input Image │ ──▶ │  Perceptual  │ ──▶ │  ECDSA   │ ──▶ │ DCT Embed │ ──▶ │ Signed Image │
│             │     │  Hash (pHash)│     │  Sign    │     │   (QIM)   │     │   (.png)     │
└─────────────┘     └──────────────┘     └──────────┘     └───────────┘     └──────────────┘
```

### Verification Pipeline

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────┐     ┌────────────┐
│ Signed Image │ ──▶ │ Extract Sig │ ──▶ │  Perceptual  │ ──▶ │  ECDSA   │ ──▶ │ AUTHENTIC  │
│              │     │  (DCT/QIM)  │     │  Hash (pHash)│     │  Verify  │     │ or TAMPERED│
└──────────────┘     └─────────────┘     └──────────────┘     └──────────┘     └────────────┘
```

## Project Structure

```
image_auth_system/
├── main.py                  # CLI entry point (genkeys / sign / verify)
├── test_scenario.py         # End-to-end sign → verify → tamper → verify test
├── test_dct_robustness.py   # JPEG compression & resize robustness tests
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── modules/
│   ├── __init__.py
│   ├── image_io.py          # Image loading & saving (OpenCV)
│   ├── hashing.py           # SHA-256 hashing of raw pixel data
│   ├── signature.py         # ECDSA P-256 key gen, signing, verification
│   ├── embedding.py         # DCT-domain QIM embed/extract with redundancy
│   └── verification.py      # Full verification pipeline + perceptual hashing
├── keys/                    # Generated key pair (created by genkeys)
├── signed_images/           # Signed output images
└── test_images/             # Test artifacts
```

## How It Works

### Signing

1. **Load** the input image (any format OpenCV supports).
2. **Compute a perceptual hash** — a block-mean hash over an NxN grid of the grayscale image, thresholded against the median. This hash is stable across JPEG compression but changes on meaningful edits.
3. **Sign the hash** using ECDSA with the P-256 curve (SHA-256 internally).
4. **Embed the signature** into the Y (luminance) channel using DCT-domain QIM:
   - The image is converted to YCrCb color space.
   - The Y channel is divided into 8×8 blocks.
   - For each block, mid-frequency DCT coefficients are quantized to encode signature bits.
   - A 32-bit header stores the signature length, followed by the signature bitstream.
   - Redundant copies are embedded for error resilience (majority voting on extraction).
5. **Save** the signed image as lossless PNG.

### Verification

1. **Load** the signed image.
2. **Extract** the embedded signature from DCT coefficients using majority voting across redundant copies.
3. **Recompute** the perceptual hash of the image.
4. **Verify** the extracted ECDSA signature against the recomputed hash using the public key.
5. **Output**: `AUTHENTIC` if valid, `TAMPERED` otherwise.

## Getting Started

### Prerequisites

- **Python 3.8+**

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/image-auth-system.git
cd image-auth-system

# (Recommended) Create a virtual environment
python -m venv venv

# Activate it
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Generate Keys

Generate an ECDSA P-256 key pair (stored in `keys/`):

```bash
python main.py genkeys
```

### Sign an Image

```bash
python main.py sign path/to/photo.jpg signed_images/photo_signed.png
```

> The output must be `.png` (lossless) to preserve the embedded data.

### Verify a Signed Image

```bash
python main.py verify signed_images/photo_signed.png
```

Output:

```
  ========================================
   Result: AUTHENTIC
  ========================================
```

or if tampered:

```
  ========================================
   Result: TAMPERED
  ========================================
```

## Running Tests

### Basic Sign / Verify / Tamper Test

```bash
python test_scenario.py
```

Signs a generated test image, verifies it (expects `AUTHENTIC`), tampers with it by overwriting a region, and verifies again (expects `TAMPERED`).

### DCT Robustness Test

```bash
python test_dct_robustness.py
```

Tests signature survival across JPEG compression at various quality levels and resize round-trips.

## Technical Details

| Parameter          | Value                                              |
| ------------------ | -------------------------------------------------- |
| Signature Scheme   | ECDSA with NIST P-256 curve                        |
| Hash (for signing) | Perceptual block-mean hash (16×16 grid)            |
| Hash (pixel-level) | SHA-256                                            |
| Embedding Domain   | DCT (Y channel of YCrCb)                           |
| Embedding Method   | QIM (Quantization Index Modulation)                 |
| DCT Positions      | Mid-frequency: (3,2), (2,3), (4,1), (1,4)         |
| Quantization Step  | 35.0                                               |
| Redundancy         | Up to 21× with majority voting                     |
| Header Size        | 32 bits                                            |
| Signature Size     | ~70–72 bytes (ECDSA P-256, DER encoded)            |

## Dependencies

| Package        | Purpose                         |
| -------------- | ------------------------------- |
| opencv-python  | Image I/O and DCT transforms   |
| numpy          | Array operations                |
| Pillow         | Image format support            |
| cryptography   | ECDSA key gen, signing, verify  |
| scipy          | Signal processing utilities     |

## Notes

- Signed images should be saved and shared as **PNG**. While the DCT embedding is designed to survive moderate JPEG compression, PNG guarantees no data loss.
- Each user must run `python main.py genkeys` to generate their own key pair. Private keys are excluded from version control via `.gitignore`.
- Minimum recommended image size: **128×128 pixels** (larger images = more embedding capacity and redundancy).

## Full-Stack Web Application

This repository now includes a complete web-based educational dashboard for signing and verifying images.

### Added Structure

```
image_auth_system/
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── schemas.py
│       ├── api/
│       │   └── routes.py
│       └── services/
│           └── auth_service.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── styles.css
        └── components/
            ├── UploadCard.jsx
            ├── StepCard.jsx
            └── VerificationPanel.jsx
```

### Backend (FastAPI)

API endpoints:

- `POST /sign-image`
  - Input: multipart image file (`image`)
  - Output includes hash, full signature, signature preview, embedding info, base64 signed image, and debug step logs.
- `POST /verify-image`
  - Input: multipart image file (`image`)
  - Output includes extracted signature, recomputed hash, validity flag, and authenticity message.

Run backend:

```bash
cd ..
python -m venv .venv

# Windows
.venv\Scripts\activate

cd image_auth_system/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (React + Vite)

The dashboard includes:

- Drag-and-drop image upload with preview
- Step-by-step visualization cards (image load, hash, signature, embedding, signed image)
- Expand/collapse for long content and tooltip-style explain labels
- Animated progress and loading states
- Verification panel with extracted signature, recomputed hash, and authentic/tampered badge
- Processing logs panel for transparent debugging flow

Run frontend:

```bash
cd image_auth_system/frontend
npm install
npm run dev
```

Optional API URL override (if backend is not on default `http://127.0.0.1:8000`):

```bash
# Windows PowerShell example
$env:VITE_API_URL="http://127.0.0.1:8000"
npm run dev
```

## License

Academic / research use.
