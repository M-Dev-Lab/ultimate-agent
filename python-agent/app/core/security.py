"""
Security utilities for authentication, token generation, and password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


# Password hashing context - use argon2 for better security and flexibility
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# JWT Configuration
ALGORITHM = settings.jwt_algorithm
SECRET_KEY = settings.jwt_secret.get_secret_value()


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data"""
    sub: str  # Subject (usually user_id or username)
    exp: datetime
    iat: datetime
    scopes: list = []


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> Token:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token (typically {'sub': user_id})
        expires_delta: Optional expiration time delta
        
    Returns:
        Token object with access_token, token_type, and expires_in
        
    Raises:
        ValueError: If data is invalid
    """
    if not data or "sub" not in data:
        raise ValueError("Token data must contain 'sub' field")
    
    # Make a copy to avoid modifying the original
    to_encode = data.copy()
    
    # Set expiration time
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(hours=settings.jwt_expiration_hours)
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": now_utc
    })
    
    # Encode the token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    # Calculate expires_in in seconds
    expires_in = int((expire - now_utc).total_seconds())
    
    return Token(
        access_token=encoded_jwt,
        token_type="bearer",
        expires_in=expires_in
    )


def verify_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData with decoded payload
        
    Raises:
        JWTError: If token is invalid or expired
        ValueError: If token payload is invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify required claims
        if "sub" not in payload:
            raise ValueError("Token must contain 'sub' claim")
        
        token_data = TokenData(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
            scopes=payload.get("scopes", [])
        )
        return token_data
        
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")


def decode_token_payload(token: str) -> Dict[str, Any]:
    """
    Decode token payload without strict validation.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dictionary
        
    Raises:
        JWTError: If token is malformed
    """
    try:
        # Decode without verification for payload inspection
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        raise JWTError(f"Failed to decode token: {str(e)}")
