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
    response = client.post("/VoltaireAI/chat", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "intent" in data

def test_get_settings_endpoint():
    """测试获取配置端点"""
    response = client.get("/VoltaireAI/settings")

    assert response.status_code == 200
    data = response.json()
    assert "model_sources" in data
    assert "main_workflow" in data

def test_update_settings_endpoint():
    """测试更新配置端点"""
    import copy
    from config.config_loader import load_settings, save_settings

    # Save original settings to restore later
    original_settings = load_settings()

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
        "main_workflow": "workflows/main.json",
        "default_model_source": "test_model"
    }

    try:
        response = client.post("/VoltaireAI/settings", json=new_settings)

        assert response.status_code == 200
        assert response.json()["message"] == "Settings updated successfully"
    finally:
        # Restore original settings
        save_settings(original_settings)


def test_execution_feedback_success():
    """测试执行反馈端点（成功）"""
    feedback_data = {
        "status": "success",
        "message": "操作执行成功",
        "original_request": "点击登录按钮",
        "site_id": "test-site"
    }
    response = client.post("/VoltaireAI/execution-feedback", json=feedback_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "acknowledged"


def test_execution_feedback_failure():
    """测试执行反馈端点（失败）"""
    feedback_data = {
        "status": "failed",
        "message": "元素未找到: #login-btn",
        "original_request": "点击登录按钮",
        "site_id": "test-site"
    }
    response = client.post("/VoltaireAI/execution-feedback", json=feedback_data)

    assert response.status_code == 200
    data = response.json()
    # Should provide retry or acknowledge the failure
    assert "status" in data
    assert "message" in data