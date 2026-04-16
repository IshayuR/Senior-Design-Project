from hashlib import sha256

from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from app.database.mongo import email_match_filter, get_user_collection
from app.models.auth import LoginRequest, LoginResponse


router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(raw: str) -> str:
    # Simple, prototype-only hashing. Replace with bcrypt/argon2 in production.
    return sha256(raw.encode("utf-8")).hexdigest()


def _as_int_restaurant_id(value: object) -> int | None:
    """Parse numeric restaurant id, or None if value is a non-numeric slug (e.g. device name)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return int(s)
    return None


def _get_restaurant_id(user: dict) -> int:
    """Top-level restaurantId, or first numeric id in restaurants[]; default 1 for legacy SQLite keys."""
    rid = _as_int_restaurant_id(user.get("restaurantId"))
    if rid is not None:
        return rid
    for entry in user.get("restaurants") or []:
        if isinstance(entry, dict):
            for key in ("restaurantId", "id", "numericId"):
                nested = _as_int_restaurant_id(entry.get(key))
                if nested is not None:
                    return nested
        else:
            nested = _as_int_restaurant_id(entry)
            if nested is not None:
                return nested
    return 1


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> dict:
    try:
        users = get_user_collection()
        user = users.find_one(email_match_filter(payload.email))
    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Support plain "password" for testing; otherwise use "passwordHash"
    expected_hash = user.get("passwordHash")
    plain = user.get("password")
    if expected_hash:
        if _hash_password(payload.password) != expected_hash:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    elif plain is not None and plain == payload.password:
        pass  # plain password match (dev only)
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    restaurant_id = _get_restaurant_id(user)
    name = user.get("name") or payload.email

    stored_email = user.get("email") or payload.email.strip()

    return {
        "email": stored_email,
        "name": name,
        "restaurantId": restaurant_id,
    }

