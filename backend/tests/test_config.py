# backend/tests/test_config.py
import pytest
import json
import os
import tempfile
from backend.config.config_loader import load_settings, save_settings

def test_load_settings_creates_default():
    """测试加载配置,不存在时创建默认配置"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "test_settings.json")

        settings = load_settings(test_path)

        assert "model_sources" in settings
        assert isinstance(settings["model_sources"], list)
        assert len(settings["model_sources"]) > 0
        assert "main_workflow" in settings

def test_save_and_load_settings():
    """测试保存和加载配置"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "test_settings.json")
        test_data = {
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

        save_settings(test_data, test_path)
        loaded = load_settings(test_path)

        assert loaded["model_sources"][0]["name"] == "test_model"
        assert loaded["main_workflow"] == "workflows/main.json"

def test_default_settings_structure():
    """测试默认配置结构完整性"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "test_settings.json")
        settings = load_settings(test_path)

        # 检查model_sources结构
        model_source = settings["model_sources"][0]
        assert "name" in model_source
        assert "api_format" in model_source
        assert "base_url" in model_source
        assert "api_key" in model_source
        assert "model" in model_source