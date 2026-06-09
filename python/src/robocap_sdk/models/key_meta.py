from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from robocap_sdk.config import RSA_BITS


class RsaKeyMeta(BaseModel):
    rsa_key_version: int = Field(..., ge=1)
    effective_at: datetime
    device_id: str
    rsa_bits: int = Field(default=RSA_BITS)
