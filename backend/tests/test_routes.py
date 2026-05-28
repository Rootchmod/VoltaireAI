# backend/tests/test_routes.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.models import ChatRequest

client = TestClient(app, raise_server_exceptions=True)

def test_root_endpoint():
    """测试根端点"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_health_endpoint():
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_chat_endpoint():
    """测试聊天端点"""
    request_data = {
        "message": "帮我点击登录按钮",
        "site_id": "test-site"
    }
    response = client.post("/api/chat", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "intent" in data

def test_get_settings_endpoint():
    """测试获取配置端点"""
    response = client.get("/api/settings")

    assert response.status_code == 200
    data = response.json()
    assert "model_sources" in data
    assert "main_workflow" in data

def test_update_settings_endpoint():
    """测试更新配置端点"""
    new_settings = {
        "model_sources": [
            {
                "name": "test_model",
                "api_format": "OpenAI",
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-key",
                "model": "gpt-4"
            }
        ],
        "main_workflow": "workflows/main.json"
    }

    response = client.post("/api/settings", json=new_settings)

    assert response.status_code == 200
    assert response.json()["message"] == "Settings updated successfully"