import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os

client = TestClient(app)

@patch("backend.main.boto3.client")
@patch("backend.main.httpx.AsyncClient")
def test_submit_feedback_success(mock_httpx_client, mock_boto3_client):
    # Mock Bedrock
    mock_bedrock = MagicMock()
    mock_boto3_client.return_value = mock_bedrock
    
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
    
    # Mock httpx
    mock_async_client = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_async_client
    
    mock_gh_response = MagicMock()
    mock_gh_response.status_code = 201
    mock_gh_response.json.return_value = {"html_url": "https://github.com/j-kokoszka/set/issues/1"}
    mock_async_client.post.return_value = mock_gh_response
    
    # Set environment variable
    with patch.dict(os.environ, {"GITHUB_PAT": "fake_pat"}):
        headers = {"Authorization": "Bearer mock_user_123"}
        payload = {"text": "I found a bug in the workout save button."}
        
        resp = client.post("/feedback", json=payload, headers=headers)
        
        assert resp.status_code == 200
        assert resp.json()["message"] == "Feedback submitted successfully"
        assert resp.json()["issue_url"] == "https://github.com/j-kokoszka/set/issues/1"
        
        # Verify Bedrock call
        mock_bedrock.invoke_model.assert_called_once()
        
        # Verify GitHub call
        mock_async_client.post.assert_called_once()
        args, kwargs = mock_async_client.post.call_args
        assert kwargs["json"]["title"] == "Bug Report"
        assert "Submitted by: user_123" in kwargs["json"]["body"]
        assert kwargs["json"]["labels"] == ["bug"]

@patch("backend.main.boto3.client")
@patch("backend.main.httpx.AsyncClient")
def test_submit_feedback_bedrock_failure_fallback(mock_httpx_client, mock_boto3_client):
    # Mock Bedrock failure
    mock_bedrock = MagicMock()
    mock_boto3_client.return_value = mock_bedrock
    mock_bedrock.invoke_model.side_effect = Exception("Bedrock error")
    
    # Mock httpx
    mock_async_client = AsyncMock()
    mock_httpx_client.return_value.__aenter__.return_value = mock_async_client
    
    mock_gh_response = MagicMock()
    mock_gh_response.status_code = 201
    mock_gh_response.json.return_value = {"html_url": "https://github.com/j-kokoszka/set/issues/2"}
    mock_async_client.post.return_value = mock_gh_response
    
    with patch.dict(os.environ, {"GITHUB_PAT": "fake_pat"}):
        headers = {"Authorization": "Bearer mock_user_123"}
        payload = {"text": "Just some feedback."}
        
        resp = client.post("/feedback", json=payload, headers=headers)
        
        assert resp.status_code == 200
        # Verify fallback values
        args, kwargs = mock_async_client.post.call_args
        assert kwargs["json"]["title"] == "User Feedback"
        assert "Just some feedback." in kwargs["json"]["body"]
        assert kwargs["json"]["labels"] == ["feedback"]
