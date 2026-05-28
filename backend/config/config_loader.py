# backend/config/config_loader.py
import json
import os
from typing import Dict, Any, Optional

DEFAULT_SETTINGS = {
    "model_sources": [
        {
            "name": "default_openai",
            "api_format": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-4"
        },
        {
            "name": "default_anthropic",
            "api_format": "Anthropic",
            "base_url": "https://api.anthropic.com",
            "api_key": "",
            "model": "claude-3-sonnet-20240229"
        }
    ],
    "main_workflow": "workflows/main.json"
}

def load_settings(config_path: str = "backend/config/settings.json") -> Dict[str, Any]:
    """
    加载配置文件,不存在则创建默认配置

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    if not os.path.exists(config_path):
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        save_settings(DEFAULT_SETTINGS, config_path)
        return DEFAULT_SETTINGS.copy()

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_settings(settings: Dict[str, Any], config_path: str = "backend/config/settings.json") -> None:
    """
    保存配置到文件

    Args:
        settings: 配置字典
        config_path: 配置文件路径
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)