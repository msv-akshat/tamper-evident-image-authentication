from typing import Any, Dict, List

from pydantic import BaseModel, Field


class EmbeddingInfo(BaseModel):
    method: str
    description: str


class SignImageResponse(BaseModel):
    hash: str
    signature: str
    signature_preview: str
    embedding_info: EmbeddingInfo
    embedding_debug: Dict[str, Any] = Field(default_factory=dict)
    signed_image: str
    debug_steps: List[str] = Field(default_factory=list)


class VerifyImageResponse(BaseModel):
    extracted_signature: str
    recomputed_hash: str
    is_valid: bool
    message: str
    comparison_details: Dict[str, Any] = Field(default_factory=dict)
