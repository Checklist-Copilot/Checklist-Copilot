from datetime import UTC, datetime, timedelta
import base64
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _normalize_password_input(password: str) -> str:
    # bcrypt accepts up to 72 bytes; normalize long inputs deterministically.
    password_bytes = password.encode("utf-8")
    if len(password_bytes) <= 72:
        return password
    digest = hashlib.sha256(password_bytes).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii")


def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize_password_input(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_normalize_password_input(plain_password), hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
