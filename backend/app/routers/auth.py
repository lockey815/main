
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import (
    create_token,
    current_user,
    verify_password,
    hash_password,
)
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()

    if len(body.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters"
        )

    existing = db.scalar(
        select(User).where(User.email == email)
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )

    user = User(
        email=email,
        password_hash=hash_password(body.password)
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )

    return TokenOut(
        access_token=create_token(user),
        email=user.email
    )


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(
            User.email == body.email.strip().lower()
        )
    )

    if user is None or not verify_password(
        body.password, user.password_hash
    ):
        raise HTTPException(401, "Incorrect email or password")

    return TokenOut(
        access_token=create_token(user),
        email=user.email
    )


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}
