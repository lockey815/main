"""Email + password accounts with JWT bearer tokens. Passwords use scrypt from the stdlib."""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

_bearer = HTTPBearer(auto_error=False)
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, dk_b64 = stored.split("$")
        salt, dk = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
        test = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
        return hmac.compare_digest(dk, test)
    except Exception:
        return False


def create_token(user: User) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(hours=s.token_hours)
    return jwt.encode({"sub": user.id, "email": user.email, "exp": exp}, s.secret_key, algorithm="HS256")


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> User:
    unauthorised = HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if cred is None:
        raise unauthorised
    try:
        data = jwt.decode(cred.credentials, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise unauthorised
    user = db.get(User, data.get("sub"))
    if user is None:
        raise unauthorised
    return user


def ensure_user(db: Session, email: str, password: str) -> User:
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
