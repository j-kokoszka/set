import os
import httpx
from fastapi import Header, HTTPException, status
from jose import jwt, JWTError
import structlog
from typing import Optional

logger = structlog.get_logger()

# AWS Cognito Settings
AWS_REGION = os.getenv("SET_AWS_REGION", "eu-central-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")
MOCK_AUTH = os.getenv("MOCK_AUTH", "false").lower() == "true"

# JWKS Caching
JWKS_URL = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
_jwks_cache = None

async def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(JWKS_URL, timeout=5.0)
                response.raise_for_status()
                _jwks_cache = response.json()
                logger.info("JWKS fetched and cached")
        except Exception as e:
            logger.error("failed_to_fetch_jwks", error=str(e), url=JWKS_URL)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    return _jwks_cache

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

    if not COGNITO_USER_POOL_ID or not COGNITO_APP_CLIENT_ID:
        logger.error("cognito_not_configured", pool_id=COGNITO_USER_POOL_ID, client_id=COGNITO_APP_CLIENT_ID)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured"
        )

    try:
        # 1. Get the key ID from the header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise JWTError("Missing kid in header")

        # 2. Find the correct public key in JWKS
        jwks = await get_jwks()
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if not key:
            # Force refresh cache once if key not found
            global _jwks_cache
            _jwks_cache = None
            jwks = await get_jwks()
            key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
            if not key:
                raise JWTError("Public key not found in JWKS")

        # 3. Decode and validate the token
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=COGNITO_APP_CLIENT_ID,
            issuer=f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
        )
        
        # 4. Extract user identifier
        user_id = payload.get("sub") or payload.get("username") or payload.get("email")
        if not user_id:
            raise JWTError("Token missing user identifier")
            
        return user_id

    except JWTError as e:
        logger.warning("invalid_token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except Exception as e:
        logger.error("token_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )
