import asyncio
import pytest
from fastapi import HTTPException
import auth
from jose import jwt

def test_get_current_user_missing_header():
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(auth.get_current_user(None))
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid authentication header"

def test_get_current_user_invalid_format():
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(auth.get_current_user("Token 123"))
    assert excinfo.value.status_code == 401

def test_get_current_user_mock_success(monkeypatch):
    monkeypatch.setattr(auth, "MOCK_AUTH", True)
    
    user_id = asyncio.run(auth.get_current_user("Bearer mock_user123"))
    assert user_id == "user123"

def test_get_current_user_mock_failure(monkeypatch):
    monkeypatch.setattr(auth, "MOCK_AUTH", True)
    
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(auth.get_current_user("Bearer invalid_token"))
    assert excinfo.value.status_code == 401
    assert "Mock auth failed" in excinfo.value.detail

def test_get_current_user_no_cognito_config(monkeypatch):
    monkeypatch.setattr(auth, "MOCK_AUTH", False)
    monkeypatch.setattr(auth, "COGNITO_USER_POOL_ID", None)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(auth.get_current_user("Bearer some_token"))
    assert excinfo.value.status_code == 500
    assert "Authentication not configured" in excinfo.value.detail

@pytest.mark.asyncio
async def test_get_jwks_success(monkeypatch):
    class MockResponse:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"keys": [{"kid": "123", "alg": "RS256"}]}

    async def mock_get(*args, **kwargs):
        return MockResponse()

    # Reset cache and mock httpx
    monkeypatch.setattr(auth, "_jwks_cache", None)
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    jwks = await auth.get_jwks()
    assert jwks["keys"][0]["kid"] == "123"

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(monkeypatch):
    monkeypatch.setattr(auth, "MOCK_AUTH", False)
    monkeypatch.setattr(auth, "COGNITO_USER_POOL_ID", "pool123")
    monkeypatch.setattr(auth, "COGNITO_APP_CLIENT_ID", "client123")

    # Mock jwks
    async def mock_jwks():
        return {"keys": []}
    monkeypatch.setattr(auth, "get_jwks", mock_jwks)

    with pytest.raises(HTTPException) as excinfo:
        await auth.get_current_user("Bearer invalid.token.string")
    assert excinfo.value.status_code == 401
    assert "Invalid token" in excinfo.value.detail

@pytest.mark.asyncio
async def test_get_current_user_token_use_validation(monkeypatch):
    monkeypatch.setattr(auth, "MOCK_AUTH", False)
    monkeypatch.setattr(auth, "COGNITO_USER_POOL_ID", "pool123")
    monkeypatch.setattr(auth, "COGNITO_APP_CLIENT_ID", "client123")

    # Mock get_unverified_header
    monkeypatch.setattr("jose.jwt.get_unverified_header", lambda t: {"kid": "123"})
    
    # Mock get_jwks
    async def mock_jwks():
        return {"keys": [{"kid": "123", "alg": "RS256"}]}
    monkeypatch.setattr(auth, "get_jwks", mock_jwks)

    # Mock jwt.decode
    decoded_options = {}
    def mock_decode(token, key, **kwargs):
        nonlocal decoded_options
        decoded_options = kwargs.get("options", {})
        if "id_token" in token:
            return {"token_use": "id", "aud": "client123", "sub": "sub123", "email": "user@example.com"}
        if "access_token" in token:
            return {"token_use": "access", "client_id": "client123", "sub": "sub123"}
        if "wrong_client" in token:
            return {"token_use": "id", "aud": "wrong", "sub": "sub123"}
        if "no_email" in token:
            return {"token_use": "id", "aud": "client123", "sub": "sub123"}
        return {}

    monkeypatch.setattr("jose.jwt.decode", mock_decode)

    # Test ID token success - should use email
    user_id = await auth.get_current_user("Bearer id_token")
    assert user_id == "user@example.com"
    assert decoded_options.get("verify_at_hash") is False

    # Test Access token - should now fail (only ID tokens supported for email stability)
    with pytest.raises(HTTPException) as excinfo:
        await auth.get_current_user("Bearer access_token")
    assert excinfo.value.status_code == 401
    assert "Only ID tokens are supported" in excinfo.value.detail

    # Test ID token without email
    with pytest.raises(HTTPException) as excinfo:
        await auth.get_current_user("Bearer no_email")
    assert excinfo.value.status_code == 401
    assert "ID Token missing email claim" in excinfo.value.detail

    # Test wrong client ID
    with pytest.raises(HTTPException) as excinfo:
        await auth.get_current_user("Bearer wrong_client")
    assert excinfo.value.status_code == 401
    assert "Token not intended for this application" in excinfo.value.detail

    # Test invalid token_use
    with pytest.raises(HTTPException) as excinfo:
        await auth.get_current_user("Bearer invalid_use")
    assert excinfo.value.status_code == 401
    assert "Only ID tokens are supported" in excinfo.value.detail
