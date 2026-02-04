"""
Authentication & Authorization Layer
JWT-based authentication with role-based access control
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional as TypingOptional
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme for FastAPI
security = HTTPBearer()


class TokenManager:
    """Manages JWT token creation and validation"""

    @staticmethod
    def create_access_token(
        user_id: str,
        permissions: Optional[list] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create JWT access token"""
        if expires_delta is None:
            expires_delta = timedelta(hours=settings.jwt_expiration_hours)

        to_encode = {
            "sub": user_id,
            "permissions": permissions or [],
            "exp": datetime.now(timezone.utc) + expires_delta,
            "iat": datetime.now(timezone.utc),
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret.get_secret_value(),
                algorithms=[settings.jwt_algorithm],
            )
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create refresh token (longer expiration)"""
        expires_delta = timedelta(days=7)
        return TokenManager.create_access_token(user_id, expires_delta=expires_delta)


class PasswordManager:
    """Manages password hashing and verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against hash"""
        return pwd_context.verify(plain_password, hashed_password)


class APIKeyManager:
    """Manages API key generation and validation"""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure random API key"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage"""
        return pwd_context.hash(api_key)

    @staticmethod
    def verify_api_key(plain_key: str, hashed_key: str) -> bool:
        """Verify API key"""
        return pwd_context.verify(plain_key, hashed_key)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Dependency to extract and verify current user from JWT token
    Use in FastAPI route parameters: async def my_route(user = Depends(get_current_user))
    """
    token = credentials.credentials
    payload = TokenManager.verify_token(token)
    return payload


async def get_current_user_or_default(
    authorization: TypingOptional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Optional authentication - returns default user in development mode or with valid token
    """
    from app.core.config import settings
    
    # Try to verify token from Authorization header
    if authorization:
        try:
            if authorization.startswith("Bearer "):
                token = authorization[7:]
                payload = TokenManager.verify_token(token)
                return payload
        except Exception:
            pass
    
    # In development mode, return a default user
    if settings.environment == "development":
        return {
            "sub": "telegram-bot",
            "permissions": ["build", "analysis", "memory"],
            "type": "bot"
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


async def require_admin(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Dependency to require admin permissions"""
    if "admin" not in user.get("permissions", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required",
        )
    return user


async def require_permission(permission: str):
    """Factory to create permission requirement dependency"""
    async def _check_permission(
        user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        if permission not in user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return user

    return _check_permission


class RBAC:
    """Role-Based Access Control"""

    ROLES = {
        "admin": ["read", "write", "delete", "admin", "audit"],
        "user": ["read", "write"],
        "viewer": ["read"],
    }

    @staticmethod
    def get_permissions_for_role(role: str) -> list:
        """Get permissions for a role"""
        return RBAC.ROLES.get(role, [])

    @staticmethod
    def has_permission(permissions: list, required_permission: str) -> bool:
        """Check if user has required permission"""
        return required_permission in permissions


# Export verify_token for convenience
verify_token = TokenManager.verify_token
