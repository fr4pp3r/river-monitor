"""
Session-based authentication and role enforcement for the dashboard.

Passwords are stored as PBKDF2-HMAC-SHA256 hashes (stdlib only). Sessions are
signed cookies handled by Starlette's SessionMiddleware. Two roles exist:
"viewer" (read-only) and "admin" (may change config, contacts and alerts).
"""

import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, Request, status

from src.settings import settings
from src.data.database import (
    count_users, insert_user, get_user_by_username, update_user, log_audit,
)

_PBKDF2_ITERATIONS = 260000
_PBKDF2_ALGO = "sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGO, password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            _PBKDF2_ALGO, password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def authenticate_user(username: str, password: str) -> Optional[dict]:
    if not username or not password:
        return None
    user = get_user_by_username(username)
    if not user or not user.get("is_active"):
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return user


def ensure_default_admin() -> None:
    if count_users() > 0:
        return
    username = settings.admin_username
    password = settings.admin_password
    insert_user(username, hash_password(password), role="admin")
    from loguru import logger
    if password == "admin":
        logger.warning(
            "Created default admin user '{}' with the default password. "
            "Set ADMIN_PASSWORD in .env before deployment.", username
        )
    else:
        logger.info("Created default admin user '{}'", username)


def session_user(request: Request) -> Optional[dict]:
    user = request.session.get("user") if hasattr(request, "session") else None
    if not user:
        return None
    return user


def is_authenticated(request: Request) -> bool:
    return session_user(request) is not None


def is_admin(request: Request) -> bool:
    user = session_user(request)
    return bool(user and user.get("role") == "admin")


def _auth_required() -> bool:
    return settings.auth_enabled


def require_user(request: Request) -> dict:
    if not _auth_required():
        return {"username": "anonymous", "role": "admin", "user_id": None}
    user = session_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_admin(request: Request) -> dict:
    if not _auth_required():
        return {"username": "anonymous", "role": "admin", "user_id": None}
    user = session_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return user


def login_user(request: Request, user: dict) -> None:
    request.session["user"] = {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
    }
    update_user(user["id"], last_login=datetime.now().isoformat())
    log_audit(
        action="login",
        actor=user["username"],
        role=user["role"],
        target="session",
        ip_address=request.client.host if request.client else None,
    )


def logout_user(request: Request) -> None:
    user = session_user(request)
    request.session.pop("user", None)
    if user:
        log_audit(
            action="logout",
            actor=user.get("username"),
            role=user.get("role"),
            target="session",
            ip_address=request.client.host if request.client else None,
        )


PUBLIC_PATHS = {"/login", "/api/auth/login", "/api/auth/logout", "/api/auth/me", "/healthz", "/readyz"}
PUBLIC_PREFIXES = ("/static/",)


def is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)
