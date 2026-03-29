# Tamper-Evident Image Authentication System

A complete image authenticity system with two interfaces:

- A Python CLI for cryptographic signing and verification.
- A full-stack web app (FastAPI + React) that explains each processing step visually.

The core idea is to generate a digital signature from an image fingerprint, then embed that signature inside the image's DCT frequency domain. During verification, the signature is extracted and checked against a recomputed fingerprint. If they match, the image is authentic; otherwise, it is flagged as tampered.

## Why This Project Exists

Many image integrity approaches fail in practical workflows because images are compressed, resized, or lightly transformed. Pure pixel-level checks are fragile. This project combines:

- Robust image fingerprinting (perceptual hash pipeline)
- Public-key cryptography (ECDSA P-256)
- Frequency-domain embedding (DCT + QIM)

to make authenticity verification both secure and practical.

## How It Works

### Signing pipeline

1. Load input image.
2. Compute a robust perceptual fingerprint.
3. Hash fingerprint with SHA-256.
4. Sign hash with ECDSA private key.
5. Embed signature bits into selected DCT coefficients in Y channel.
6. Save signed output as PNG.

### Verification pipeline

1. Load signed image.
2. Extract embedded signature from DCT coefficients.
3. Recompute robust fingerprint and SHA-256 hash.
4. Verify extracted signature using ECDSA public key.
5. Return `Authentic` or `Tampered`.

### High-level flow diagrams

Signing:

```
Input Image
  -> Robust Hash
  -> SHA-256
  -> ECDSA Sign
  -> DCT/QIM Embedding
  -> Signed PNG
```

Verification:

```
Signed Image
  -> DCT/QIM Extraction
  -> Robust Hash + SHA-256
  -> ECDSA Verify
  -> Authentic / Tampered
```

## Repository Structure

```
image_auth_system/
├── main.py                         # CLI entry point (genkeys/sign/verify)
├── requirements.txt                # CLI/core Python dependencies
├── README.md
├── test_scenario.py                # End-to-end sign/verify/tamper scenario
├── test_dct_robustness.py          # Robustness checks (JPEG/resize)
├── keys/                           # Generated keypair (local)
├── signed_images/                  # Local output artifacts
├── test_images/                    # Local test artifacts
├── modules/
│   ├── image_io.py                 # Image load/save helpers
│   ├── signature.py                # ECDSA key/sign/verify logic
│   ├── embedding.py                # DCT + QIM embed/extract logic
│   ├── verification.py             # Verification pipeline utilities
│   └── hashing.py
├── backend/
│   ├── requirements.txt            # FastAPI backend dependencies
│   ├── start_backend.ps1           # Reliable Windows backend launcher
│   └── app/
│       ├── main.py                 # FastAPI app + CORS + /health
│       ├── schemas.py              # API response models
│       ├── api/routes.py           # /sign-image and /verify-image routes
│       └── services/auth_service.py# Business logic, embedding debug payloads
└── frontend/
    ├── package.json                # React + Vite scripts/deps
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx                 # Home/Sign/Verify app flow
        ├── styles.css              # UI styling
        └── components/
            ├── UploadCard.jsx
            ├── StepCard.jsx
            └── VerificationPanel.jsx
```

## Core Crypto + Embedding Details

- Signature scheme: ECDSA (NIST P-256)
- Signed value: SHA-256 of robust image hash string
- Embedding domain: DCT in Y channel (YCrCb color space)
- Embedding method: QIM (Quantization Index Modulation)
- Block size: 8x8
- Header: 32-bit signature length prefix
- DCT positions: `(3,2), (2,3), (4,1), (1,4)`
- Redundancy: repeated payload embedding with majority-style resilience in extraction

This design balances invisibility and survivability better than simple LSB methods.

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+
- Windows PowerShell (for `backend/start_backend.ps1`)

## Quick Start (Full Stack)

### 1) Create and activate Python environment (repo root)

Windows PowerShell:

```powershell
Set-Location D:\Tamper_Detection_crypto
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install Python dependencies

```powershell
Set-Location .\image_auth_system
pip install -r requirements.txt
pip install -r .\backend\requirements.txt
```

### 3) Run backend API

Recommended (uses the known-good interpreter path):

```powershell
Set-Location .\backend
.\start_backend.ps1
```

Alternative:

```powershell
Set-Location .\backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URL: `http://127.0.0.1:8000`

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### 4) Run frontend

```powershell
Set-Location ..\frontend
npm install
npm run dev
```

Frontend URL: usually `http://127.0.0.1:5173`

Optional API override:

```powershell
$env:VITE_API_URL="http://127.0.0.1:8000"
npm run dev
```

## CLI Usage (Core System)

From `image_auth_system` root:

### Generate keys

```bash
python main.py genkeys
python main.py genkeys --keydir keys
```

### Sign image

```bash
python main.py sign input.jpg signed_images/output.png
python main.py sign input.jpg signed_images/output.png --keyfile keys/private_key.pem
```

If output extension is not `.png`, CLI appends `.png` automatically.

### Verify image

```bash
python main.py verify signed_images/output.png
python main.py verify signed_images/output.png --keyfile keys/public_key.pem
```

Exit code behavior:

- `0`: authentic
- `1`: tampered or error

## REST API Reference

Base URL: `http://127.0.0.1:8000`

### `GET /health`

Response:

```json
{ "status": "ok" }
```

### `POST /sign-image`

Content type: `multipart/form-data`

Field:

- `image`: image file

Response fields:

- `hash`: final SHA-256 hash used for signing
- `signature`: base64 full ECDSA signature
- `signature_preview`: shortened preview string
- `embedding_info`: method + description
- `embedding_debug`: detailed DCT block/coeff visualization payload
- `signed_image`: base64 PNG of signed output
- `debug_steps`: backend processing log lines

### `POST /verify-image`

Content type: `multipart/form-data`

Field:

- `image`: image file

Response fields:

- `extracted_signature`: extracted signature (base64, empty if not found)
- `recomputed_hash`: SHA-256 hash recomputed from current image
- `is_valid`: cryptographic verification result
- `message`: `Authentic` or `Tampered`
- `comparison_details`: algorithm/rule/checklist/result metadata for UI explanation

## Frontend Behavior Guide

The UI has three modes:

- Home: choose Sign flow or Verify flow
- Signing page: upload, sign, inspect 5-step pipeline and DCT matrices
- Verification page: upload signed image and inspect exact verification logic

Important anti-mismatch flow:

- On the Signing page, use `Verify this exact signed output`.
- This sends the exact generated signed PNG bytes into the verification page.
- It avoids common mistakes such as selecting an edited/re-encoded/wrong file.

## Running Tests

### End-to-end scenario

```bash
python test_scenario.py
```

What it does:

- Generates/loads keys
- Signs a sample image
- Verifies as authentic
- Applies tamper operation
- Verifies as tampered

### Robustness checks

```bash
python test_dct_robustness.py
```

What it checks:

- JPEG compression resilience
- Resize round-trip tolerance

## Troubleshooting

### "Tampered" but image seems unchanged

Most common causes:

- Verified a different file than the generated signed PNG
- Image was re-saved/re-encoded by another tool
- Key mismatch between signing and verification

Recommended actions:

1. Use `Verify this exact signed output` from the Signing page.
2. Ensure output and sharing format is PNG.
3. Confirm one keypair is used consistently.

### `No module named uvicorn`

Use the repo root virtual environment and run backend via:

```powershell
Set-Location image_auth_system\backend
.\start_backend.ps1
```

### Backend import errors for `modules.*`

Run backend from `image_auth_system/backend` so `auth_service.py` project-root path logic resolves correctly.

### Frontend cannot reach backend

- Ensure backend is up on `127.0.0.1:8000`
- Set `VITE_API_URL` if needed

## Security Notes

- Never commit private keys. The default `.gitignore` excludes `keys/*.pem`.
- Treat generated signed images as artifacts, not source.
- CORS is currently permissive (`allow_origins=["*"]`) for development convenience.
  Tighten this before production use.

## Performance Notes

- Larger images provide more 8x8 blocks and more embedding capacity.
- Very small images may reduce robustness because fewer embedding locations are available.
- PNG is recommended to preserve embedded data exactly.

## Dependency Summary

Python backend/core:

- `fastapi`, `uvicorn`, `python-multipart`
- `opencv-python`, `numpy`, `Pillow`, `scipy`
- `cryptography`

Frontend:

- `react`, `react-dom`
- `vite`, `@vitejs/plugin-react`

## License

Academic / research use.
