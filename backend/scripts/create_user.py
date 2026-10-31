"""Create (or reset the password of) a LeukNet account.

    python scripts/create_user.py doctor@hospital.org 'a-strong-password'
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402

if len(sys.argv) != 3 or len(sys.argv[2]) < 8:
    sys.exit("usage: python scripts/create_user.py EMAIL PASSWORD   (password >= 8 characters)")

Base.metadata.create_all(bind=engine)
email, password = sys.argv[1].strip().lower(), sys.argv[2]
with SessionLocal() as db:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.password_hash = hash_password(password)
        print(f"Password updated for {email}")
    else:
        db.add(User(email=email, password_hash=hash_password(password)))
        print(f"Created {email}")
    db.commit()
