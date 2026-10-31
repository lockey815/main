from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_token, current_user, verify_password
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    # same error for unknown e-mail and wrong password
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return TokenOut(access_token=create_token(user), email=user.email)


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}
