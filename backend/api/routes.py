# backend/api/routes.py
from fastapi import APIRouter, HTTPException
from backend.api.models import ChatRequest, ChatResponse, IntentType
from backend.config.config_loader import load_settings, save_settings

router = APIRouter(prefix="/api", tags=["api"])

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    处理聊天请求

    Args:
        request: ChatRequest包含message, site_id, optional context

    Returns:
        ChatResponse with AI response, intent, optional code
    """
    # TODO: 连接真实的AI工作流（Phase 2实现）
    # 当前返回mock响应用于测试
    return ChatResponse(
        message="AI系统正在构建中，完整功能将在Phase 2实现",
        intent=IntentType.QUESTION,
        code=None,
        checklist=None
    )

@router.get("/settings")
async def get_settings():
    """
    获取当前配置

    Returns:
        Current settings including model sources and workflow
    """
    settings = load_settings()
    return settings

@router.post("/settings")
async def update_settings(settings: dict):
    """
    更新配置

    Args:
        settings: New settings dictionary

    Returns:
        Success message
    """
    # TODO: 添加配置验证（Phase 2）
    save_settings(settings)
    return {"message": "Settings updated successfully"}