# backend/tests/test_models.py
import pytest
from backend.api.models import (
    ChatRequest,
    ChatResponse,
    CodeExecutionResult,
    IntentType,
    StepStatus
)

def test_chat_request_validation():
    """测试聊天请求模型验证"""
    request = ChatRequest(
        message="帮我点击登录按钮",
        site_id="test-site"
    )

    assert request.message == "帮我点击登录按钮"
    assert request.site_id == "test-site"
    assert request.context is None

def test_chat_request_with_context():
    """测试带上下文的聊天请求"""
    context = {"user_id": "123", "page": "login"}
    request = ChatRequest(
        message="测试消息",
        site_id="test-site",
        context=context
    )

    assert request.context == context

def test_chat_response():
    """测试聊天响应模型"""
    response = ChatResponse(
        message="AI回复内容",
        intent=IntentType.OPERATION,
        code="```js-start\nclick('#login-btn')\n```js-end",
        checklist={"plan": [], "progress": {"total": 0}}
    )

    assert response.message == "AI回复内容"
    assert response.intent == IntentType.OPERATION
    assert response.code is not None

def test_code_execution_result():
    """测试代码执行结果模型"""
    result_success = CodeExecutionResult(
        status="success",
        message="成功点击登录按钮"
    )

    assert result_success.status == "success"
    assert result_success.screenshot is None

    result_failed = CodeExecutionResult(
        status="failed",
        message="元素未找到",
        screenshot="base64data"
    )

    assert result_failed.status == "failed"
    assert result_failed.screenshot == "base64data"

def test_intent_types():
    """测试意图类型枚举"""
    assert IntentType.QUESTION == "question"
    assert IntentType.OPERATION == "operation"

def test_step_status():
    """测试步骤状态枚举"""
    assert StepStatus.PENDING == "pending"
    assert StepStatus.IN_PROGRESS == "in_progress"
    assert StepStatus.COMPLETED == "completed"
    assert StepStatus.FAILED == "failed"

def test_optional_fields():
    """测试可选字段"""
    # ChatResponse without optional fields
    response_minimal = ChatResponse(
        message="简单回复",
        intent=IntentType.QUESTION
    )

    assert response_minimal.code is None
    assert response_minimal.checklist is None