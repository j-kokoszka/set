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
