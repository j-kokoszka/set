import asyncio
import pytest
from fastapi import HTTPException
import auth

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
    assert excinfo.value.status_code == 401
    assert "Auth not configured" in excinfo.value.detail
