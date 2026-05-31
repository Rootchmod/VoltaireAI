# backend/config/config_loader.py
import json
import os
from typing import Dict, Any

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
    "main_workflow": "workflows/main.json",
    "default_model_source": "default_openai",
    "knowledge_store_path": ".voltaire_knowledge",
    "default_strategy": "hierarchical_indices"
}

def _find_config_path() -> str:
    """Find the correct config path, prioritizing the source file's directory."""
    # Priority 1: Same directory as this source file (most reliable)
    source_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(source_dir, "settings.json")
    if os.path.exists(path):
        return path

    # Priority 2: CWD-relative paths
    possible_paths = [
        "config/settings.json",  # Running from backend/
        "backend/config/settings.json",  # Running from project root
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p

    # Default: save alongside this source file
    return path

def _ensure_defaults(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Merge missing top-level keys from DEFAULT_SETTINGS to prevent corruption."""
    for key, default_value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = default_value
    return settings

def load_settings(config_path: str = None) -> Dict[str, Any]:
    """
    加载配置文件,不存在则创建默认配置

    Args:
        config_path: 配置文件路径 (optional, auto-detected if None)

    Returns:
        配置字典
    """
    if config_path is None:
        config_path = _find_config_path()

    if not os.path.exists(config_path):
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        save_settings(DEFAULT_SETTINGS, config_path)
        return DEFAULT_SETTINGS.copy()

    with open(config_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)

    # Merge missing default keys to prevent partial corruption
    settings = _ensure_defaults(settings)

    # Also ensure each model_source has all fields
    for src in settings.get("model_sources", []):
        for key in ["api_format", "api_key", "model", "base_url"]:
            if key not in src:
                src[key] = ""

    return settings

def save_settings(settings: Dict[str, Any], config_path: str = None) -> None:
    """
    保存配置到文件,自动补齐缺失字段

    Args:
        settings: 配置字典
        config_path: 配置文件路径 (optional, auto-detected if None)
    """
    if config_path is None:
        config_path = _find_config_path()

    # Ensure required top-level keys exist before saving
    settings = _ensure_defaults(settings)

    # Ensure model_sources has at least one entry
    if not settings.get("model_sources"):
        settings["model_sources"] = DEFAULT_SETTINGS["model_sources"]

    # Ensure default_model_source matches an existing source
    source_names = [s.get("name") for s in settings.get("model_sources", [])]
    if settings.get("default_model_source") not in source_names:
        settings["default_model_source"] = source_names[0] if source_names else "default_openai"

    # 确保目录存在
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
