from hashlib import sha256

from fastapi import APIRouter, HTTPException

from app.database.mongo import get_user_collection
from app.models.auth import LoginRequest, LoginResponse


router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(raw: str) -> str:
    # Simple, prototype-only hashing. Replace with bcrypt/argon2 in production.
    return sha256(raw.encode("utf-8")).hexdigest()


def _get_restaurant_id(user: dict) -> int:
    """Get restaurantId from user doc: top-level restaurantId or first entry in restaurants array."""
    rid = user.get("restaurantId")
    if rid is not None:
        return int(rid)
    restaurants = user.get("restaurants") or []
    if not restaurants:
        return 1  # default for single-restaurant app
    first = restaurants[0]
    if isinstance(first, dict):
        rid = first.get("restaurantId") or first.get("id")
    else:
        rid = first
    return int(rid) if rid is not None else 1


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> dict:
    users = get_user_collection()

    user = users.find_one({"email": payload.email})
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

    return {
        "email": payload.email,
        "name": name,
        "restaurantId": restaurant_id,
    }

