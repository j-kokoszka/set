import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os

client = TestClient(app)

@patch("backend.main.bedrock_client")
@patch("backend.main.boto3.client")
@patch("backend.main.httpx.AsyncClient")
def test_submit_feedback_success(mock_httpx_class, mock_boto3_client, mock_bedrock):
    # Mock Secrets Manager
    mock_secretsmanager = MagicMock()
    mock_boto3_client.return_value = mock_secretsmanager
    
    # Mock Bedrock response
    mock_response = MagicMock()
    mock_response.get.return_value.read.return_value = json.dumps({
        "output": {
            "message": {
                "content": [
                    {"text": '```json\n{"title": "Bug Report", "body": "The app crashes when I click save.", "labels": ["bug"]}\n```'}
                ]
            }
        }
    }).encode("utf-8")
    mock_bedrock.invoke_model.return_value = mock_response
    
    # Mock Secrets Manager response
    mock_secretsmanager.get_secret_value.return_value = {"SecretString": "fake_pat_from_sm"}
    
    # Mock httpx.AsyncClient instance
    mock_http_client = AsyncMock()
    mock_httpx_class.return_value.__aenter__.return_value = mock_http_client
    
    mock_gh_response = MagicMock()
    mock_gh_response.status_code = 201
    mock_gh_response.json.return_value = {"html_url": "https://github.com/j-kokoszka/set/issues/1"}
    mock_http_client.post.return_value = mock_gh_response
    
    # Mock database identity mapping
    with patch("database.db.get_or_create_internal_user_id") as mock_map:
        mock_map.return_value = "user_123"
        
        # Set environment variable
        with patch.dict(os.environ, {"GITHUB_PAT_SECRET_ID": "my-secret-id"}):
            headers = {"Authorization": "Bearer mock_user_123"}
            payload = {"text": "I found a bug in the workout save button."}
            
            resp = client.post("/feedback", json=payload, headers=headers)
            
            assert resp.status_code == 200
            assert resp.json()["message"] == "Feedback submitted successfully"
            assert resp.json()["issue_url"] == "https://github.com/j-kokoszka/set/issues/1"
            
            # Verify Bedrock call
            mock_bedrock.invoke_model.assert_called_once()
            
            # Verify Secrets Manager call
            mock_secretsmanager.get_secret_value.assert_called_once_with(SecretId="my-secret-id")
            
            # Verify GitHub call
            mock_http_client.post.assert_called_once()
            args, kwargs = mock_http_client.post.call_args
            assert kwargs["headers"]["Authorization"] == "token fake_pat_from_sm"
            assert kwargs["json"]["title"] == "Bug Report"
            assert "Submitted by: user_123" in kwargs["json"]["body"]
            assert kwargs["json"]["labels"] == ["bug"]

@patch("backend.main.bedrock_client")
@patch("backend.main.boto3.client")
@patch("backend.main.httpx.AsyncClient")
def test_submit_feedback_bedrock_failure_fallback(mock_httpx_class, mock_boto3_client, mock_bedrock):
    # Mock Secrets Manager
    mock_secretsmanager = MagicMock()
    mock_boto3_client.return_value = mock_secretsmanager
    
    # Mock Bedrock failure
    mock_bedrock.invoke_model.side_effect = Exception("Bedrock error")
    
    # Mock Secrets Manager response
    mock_secretsmanager.get_secret_value.return_value = {"SecretString": "fake_pat_from_sm"}
    
    # Mock httpx.AsyncClient instance
    mock_http_client = AsyncMock()
    mock_httpx_class.return_value.__aenter__.return_value = mock_http_client
    
    mock_gh_response = MagicMock()
    mock_gh_response.status_code = 201
    mock_gh_response.json.return_value = {"html_url": "https://github.com/j-kokoszka/set/issues/1"}
    mock_http_client.post.return_value = mock_gh_response
    
    # Mock database identity mapping
    with patch("database.db.get_or_create_internal_user_id") as mock_map:
        mock_map.return_value = "user_123"
        
        # Set environment variable
        with patch.dict(os.environ, {"GITHUB_PAT_SECRET_ID": "my-secret-id"}):
            headers = {"Authorization": "Bearer mock_user_123"}
            payload = {"text": "I found a bug."}
            
            resp = client.post("/feedback", json=payload, headers=headers)
            
            assert resp.status_code == 200
            # Should fallback to raw text
            assert resp.json()["message"] == "Feedback submitted successfully"
            
            args, kwargs = mock_http_client.post.call_args
            assert kwargs["json"]["body"] == "I found a bug.\n\n---\nSubmitted by: user_123"

def test_submit_feedback_too_long():
    headers = {"Authorization": "Bearer mock_user_123"}
    payload = {"text": "a" * 1001}
    
    resp = client.post("/feedback", json=payload, headers=headers)
    
    assert resp.status_code == 422
    assert "text" in resp.json()["detail"][0]["loc"]
