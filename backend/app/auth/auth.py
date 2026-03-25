# ─────────────────────────────────────────────────────────────────────────────
#  auth.py  —  JWT Authentication logic
#
#  This file contains everything related to security:
#    1. Hardcoded users (username, password, role)
#    2. Password verification
#    3. JWT token creation
#    4. JWT token validation
#    5. FastAPI dependency functions used by routes
#
#  JWT Flow (how it works):
#    Step 1 → Client sends POST /auth/login with username + password
#    Step 2 → Server verifies credentials, creates a signed JWT token
#    Step 3 → Client receives the token and stores it
#    Step 4 → Client sends the token in every request header:
#             Authorization: Bearer <token>
#    Step 5 → Server validates the token signature + expiry on each request
#    Step 6 → If valid, the route handler runs; if not, 401 is returned
# ─────────────────────────────────────────────────────────────────────────────
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt


# ── JWT Configuration ─────────────────────────────────────────────────────────
# SECRET_KEY is used to sign and verify tokens.
# ⚠️  In production: use a long random string and load it from an env variable.
#     Never hard-code it in source code.
SECRET_KEY = "super-secret-jwt-key-change-this-in-production"
ALGORITHM = "HS256"                  # Signing algorithm (HMAC + SHA-256)
ACCESS_TOKEN_EXPIRE_MINUTES = 30     # Token is valid for 30 minutes


# ── Hardcoded users ───────────────────────────────────────────────────────────
# In production: store users in a database with HASHED passwords (bcrypt).
# We use plain text here only for teaching purposes.
USERS_DB = {
    "admin": {"username": "admin", "password": "admin123", "role": "admin"},
    "user":  {"username": "user",  "password": "user123",  "role": "user"},
}


# ── OAuth2 scheme ─────────────────────────────────────────────────────────────
# Tells FastAPI:
#   • Requests must send "Authorization: Bearer <token>" header
#   • The login endpoint that issues tokens is at /auth/login
# This also adds the "Authorize" button in Swagger UI automatically.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Step 2a: Password verification ───────────────────────────────────────────
def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    Compares two passwords in a timing-safe way using secrets.compare_digest.

    Why not just use ==?
    A plain == comparison leaks timing information — an attacker can measure
    how long the comparison takes to figure out how many characters are correct.
    secrets.compare_digest always takes the same amount of time regardless.

    ⚠️  In production: store and compare HASHED passwords with passlib/bcrypt.
    """
    return secrets.compare_digest(
        plain_password.encode("utf-8"),
        stored_password.encode("utf-8"),
    )


# ── Step 2b: User lookup + password check ────────────────────────────────────
def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Looks up the user by username and verifies their password.
    Returns the user dict if valid, None if invalid.
    """
    user = USERS_DB.get(username)
    if not user:
        return None                              # user not found
    if not verify_password(password, user["password"]):
        return None                              # wrong password
    return user


# ── Step 3: JWT token creation ────────────────────────────────────────────────
def create_access_token(username: str, role: str) -> str:
    """
    Builds and signs a JWT token.

    The token payload (visible to anyone who decodes it) contains:
      sub  → username (standard JWT 'subject' claim)
      role → user's role (admin / user)
      exp  → expiry timestamp (standard JWT claim, checked automatically)

    The token is SIGNED with SECRET_KEY — only our server can create valid tokens.
    If anyone tampers with the payload, the signature check will fail.
    """
    payload = {
        "sub":  username,
        "role": role,
        "exp":  datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Step 5: Token validation dependency ──────────────────────────────────────
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency — used by routes that require any logged-in user.

    FastAPI automatically:
      1. Extracts the token from the "Authorization: Bearer <token>" header
      2. Passes it here for validation

    Raises HTTP 401 if:
      • Token is missing
      • Token signature is invalid (tampered)
      • Token has expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str     = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
    except JWTError:
        # Catches: expired tokens, bad signature, malformed tokens
        raise credentials_exception

    return {"username": username, "role": role}


# ── Step 6: Role-based access control dependency ──────────────────────────────
def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency — used by routes that require admin role.

    Calls get_current_user first (validates token), then checks the role.
    Raises HTTP 403 if the user is authenticated but is not an admin.

    HTTP 401 = not authenticated (no/bad token)
    HTTP 403 = authenticated but not authorised (wrong role)
    """
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. You do not have permission for this action.",
        )
    return current_user
