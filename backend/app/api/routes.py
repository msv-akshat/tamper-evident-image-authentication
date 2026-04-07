from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas import SignImageResponse, VerifyImageResponse
from app.services.auth_service import sign_image_bytes, verify_image_bytes

router = APIRouter()


@router.post("/sign-image", response_model=SignImageResponse)
async def sign_image(image: UploadFile = File(...)) -> SignImageResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")

    try:
        payload = await image.read()
        response = sign_image_bytes(payload)
        return SignImageResponse(**response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/verify-image", response_model=VerifyImageResponse)
async def verify_image(image: UploadFile = File(...)) -> VerifyImageResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")

    try:
        payload = await image.read()
        response = verify_image_bytes(payload)
        return VerifyImageResponse(**response)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


