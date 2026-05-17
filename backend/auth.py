import os
from fastapi import Header, HTTPException, status
from jose import jwt, JWTError
import structlog
from typing import Optional

logger = structlog.get_logger()

# AWS Cognito Settings
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
MOCK_AUTH = os.getenv("MOCK_AUTH", "false").lower() == "true"

# Scaffolding for Cognito validation
# JWKS_URL = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"

async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication header",
        )
    
    token = authorization.split(" ")[1]

    if MOCK_AUTH:
        if token.startswith("mock_"):
            user_id = token.replace("mock_", "")
            logger.info("Mock auth successful", user_id=user_id)
            return user_id
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mock auth failed: token must start with mock_",
            )

    # Scaffolding for real Cognito validation
    if not COGNITO_USER_POOL_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Auth not configured",
        )

    try:
        # TODO: Implement real Cognito JWKS validation
        # 1. Fetch JWKS from JWKS_URL
        # 2. Find the correct public key
        # 3. Decode and validate the token:
        # payload = jwt.decode(token, public_key, algorithms=['RS256'], audience=CLIENT_ID)
        # return payload['sub']
        
        # For now, this is just scaffolding.
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Cognito validation not yet implemented",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
