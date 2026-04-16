from hashlib import sha256

from fastapi import APIRouter, HTTPException

from app.database.db import get_connection
from app.models.auth import LoginRequest, LoginResponse


router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(raw: str) -> str:
    # Simple, prototype-only hashing. Replace with bcrypt/argon2 in production.
    return sha256(raw.encode("utf-8")).hexdigest()

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT email, name, password_hash, restaurant_id
            FROM users
            WHERE email = ?
            """,
            (payload.email.strip().lower(),),
        )
        user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if _hash_password(payload.password) != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "email": user["email"],
        "name": user["name"],
        "restaurantId": user["restaurant_id"],
    }
