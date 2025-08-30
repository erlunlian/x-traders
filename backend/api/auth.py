import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


def _base64url(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode().replace("+", "-").replace("/", "_").rstrip("=")


def _sign(data: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).digest()
    return _base64url(sig)


def _verify(data: str, sig: str, secret: str) -> bool:
    expected = _sign(data, secret)
    # constant-time compare
    return hmac.compare_digest(expected, sig)


def _now_ts() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())


def _get_admin_password_config() -> tuple[Optional[str], Optional[str], Optional[str]]:
    # Returns (password_plain, password_sha256, password_salt)
    return (
        os.getenv("ADMIN_PASSWORD"),
        os.getenv("ADMIN_PASSWORD_SHA256"),
        os.getenv("ADMIN_PASSWORD_SALT"),
    )


def _get_signing_secret() -> str:
    secret = os.getenv("ADMIN_JWT_SECRET") or os.getenv("ADMIN_PASSWORD")
    if not secret:
        raise RuntimeError("Admin secret not configured")
    return secret


def _check_password(provided: str) -> bool:
    pwd_plain, pwd_sha256, salt = _get_admin_password_config()
    if pwd_sha256 and salt:
        computed = hashlib.sha256((salt + provided).encode()).hexdigest()
        return hmac.compare_digest(computed, pwd_sha256)
    if pwd_plain:
        return hmac.compare_digest(provided, pwd_plain)
    return False


def _validate_token_or_raise(token: str) -> None:
    try:
        iat_str, exp_str, sig = token.split(".")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session") from None

    data = f"{iat_str}.{exp_str}"
    secret = _get_signing_secret()
    if not _verify(data, sig, secret):
        raise HTTPException(status_code=401, detail="Invalid session signature")

    now = _now_ts()
    try:
        exp = int(exp_str)
    except ValueError as err:
        raise HTTPException(status_code=401, detail="Invalid session exp") from err

    if now >= exp:
        raise HTTPException(status_code=401, detail="Session expired")


def require_admin(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin auth required")
    token = auth[len("Bearer ") :].strip()
    _validate_token_or_raise(token)


class AdminLoginRequest(BaseModel):
    password: str


@router.post("/auth/admin/login")
async def admin_login(body: AdminLoginRequest):
    if not _check_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    now = _now_ts()
    max_age = int(os.getenv("ADMIN_SESSION_TTL_SECONDS", str(60 * 60 * 8)))
    exp = now + max_age
    data = f"{now}.{exp}"

    secret = _get_signing_secret()
    sig = _sign(data, secret)
    token = f"{now}.{exp}.{sig}"

    return {"ok": True, "token": token}
