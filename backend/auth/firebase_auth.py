"""
Firebase Authentication middleware for FastAPI.
Verifies Firebase ID tokens from Authorization header.
In DEV_MODE, authentication is bypassed for local development.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.config import get_settings

logger = logging.getLogger("drishti.auth")

# Firebase Admin SDK — initialized lazily
_firebase_app = None


def _init_firebase():
    """Initialize Firebase Admin SDK if credentials are available."""
    global _firebase_app
    if _firebase_app is not None:
        return

    settings = get_settings()
    if not settings.firebase_project_id:
        logger.warning("Firebase project ID not set — auth will use dev mode.")
        return

    try:
        import firebase_admin
        from firebase_admin import credentials
        from pathlib import Path

        cred_path = Path(settings.firebase_credentials_path)
        if cred_path.exists():
            cred = credentials.Certificate(str(cred_path))
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized with service account.")
        else:
            # Try default credentials (useful in cloud environments)
            _firebase_app = firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized with default credentials.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")


class AuthenticatedUser(BaseModel):
    """Represents an authenticated user."""
    uid: str
    email: Optional[str] = None
    name: Optional[str] = None


async def get_current_user(request: Request) -> AuthenticatedUser:
    """
    FastAPI dependency to verify Firebase ID tokens.
    In DEV_MODE, returns a placeholder user for local development.
    """
    settings = get_settings()

    # Dev mode bypass
    if settings.dev_mode:
        return AuthenticatedUser(
            uid="dev-user",
            email="dev@drishti.local",
            name="Dev User",
        )

    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
        )

    token = auth_header[7:]  # Strip "Bearer "

    # Initialize Firebase if needed
    _init_firebase()

    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(token)
        return AuthenticatedUser(
            uid=decoded.get("uid", ""),
            email=decoded.get("email"),
            name=decoded.get("name"),
        )
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(e)}",
        )


# Optional dependency — makes auth optional for specific routes
async def get_optional_user(request: Request) -> Optional[AuthenticatedUser]:
    """Like get_current_user but returns None instead of raising 401."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
