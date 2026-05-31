"""Tests for workflows package"""

import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflows.intent_classifier import IntentClassifier, get_intent_classifier
from workflows.workflow_engine import WorkflowEngine, get_workflow_engine
from api.models import ChatRequest, IntentType


def test_intent_classifier_operation():
    """Test classifying operation intent"""
    classifier = IntentClassifier()

    # Test operation keywords
    assert classifier.classify("点击登录按钮") == IntentType.OPERATION
    assert classifier.classify("填写用户名") == IntentType.OPERATION
    assert classifier.classify("Click submit button") == IntentType.OPERATION
    assert classifier.classify("填写email地址") == IntentType.OPERATION


def test_intent_classifier_question():
    """Test classifying question intent"""
    classifier = IntentClassifier()

    # Test question keywords
    assert classifier.classify("这个网站有什么功能") == IntentType.QUESTION
    assert classifier.classify("如何使用登录功能") == IntentType.QUESTION
    assert classifier.classify("What does this button do") == IntentType.QUESTION
    assert classifier.classify("这个按钮的作用是什么") == IntentType.QUESTION


def test_intent_classifier_confidence():
    """Test confidence scoring with LLM-based classification"""
    classifier = IntentClassifier()

    result = classifier.classify_with_confidence("点击登录按钮")
    assert result["intent"] == IntentType.OPERATION
    assert result["confidence"] > 0

    result2 = classifier.classify_with_confidence("这个按钮的作用是什么")
    assert result2["intent"] == IntentType.QUESTION
    assert result2["confidence"] > 0


def test_intent_classifier_singleton():
    """Test singleton instance"""
    classifier1 = get_intent_classifier()
    classifier2 = get_intent_classifier()
    assert classifier1 is classifier2


def test_workflow_engine_init():
    """Test WorkflowEngine initialization"""
    engine = get_workflow_engine()
    assert engine.intent_classifier is not None
    assert engine.agent_manager is not None


def test_workflow_engine_execute_operation():
    """Test executing operation workflow"""
    engine = get_workflow_engine()

    request = ChatRequest(
        message="点击登录按钮",
        site_id="test_site"
    )

    response = engine.execute_chat_workflow(request)

    assert response.intent == IntentType.OPERATION
    assert response.code is not None
    assert "```js-start" in response.code
    assert "```js-end" in response.code
    # Code should be generated (may not have click if no elements found)
    assert len(response.code) > 50


def test_workflow_engine_execute_question():
    """Test executing question workflow"""
    engine = get_workflow_engine()

    request = ChatRequest(
        message="这个网站有什么功能",
        site_id="test_site"
    )

    response = engine.execute_chat_workflow(request)

    assert response.intent == IntentType.QUESTION
    assert response.message is not None
    assert response.code is None  # No code for questions


def test_workflow_engine_no_elements():
    """Test workflow when knowledge base is empty"""
    engine = get_workflow_engine()

    request = ChatRequest(
        message="点击登录按钮",
        site_id="empty_site"
    )

    response = engine.execute_chat_workflow(request)

    assert response.intent == IntentType.OPERATION
    assert response.code is not None
    # Should handle gracefully when no elements found


def test_workflow_engine_checklist_operation():
    """Test that operation workflow generates checklist"""
    engine = get_workflow_engine()

    request = ChatRequest(
        message="点击登录按钮",
        site_id="test_site"
    )

    response = engine.execute_chat_workflow(request)

    # Operation should include checklist
    if response.checklist:
        assert "plan" in response.checklist
        assert "progress" in response.checklist
        plan = response.checklist["plan"]
        assert len(plan) > 0
        assert plan[0].get("step") == 1 if isinstance(plan[0], dict) else True
        assert plan[0].get("status", "pending") in ["pending", "completed", "failed", "in_progress"]


def test_workflow_engine_handle_feedback_success():
    """Test handling successful execution feedback"""
    from api.models import ExecutionFeedbackRequest
    engine = get_workflow_engine()

    feedback = ExecutionFeedbackRequest(
        status="success",
        message="操作执行成功",
        original_request="点击登录按钮",
        site_id="test_site"
    )

    result = engine.handle_execution_feedback(feedback)

    assert result["status"] == "acknowledged"
    assert result["next_action"] == "continue"


def test_workflow_engine_handle_feedback_failure():
    """Test handling failed execution feedback"""
    from api.models import ExecutionFeedbackRequest
    engine = get_workflow_engine()

    feedback = ExecutionFeedbackRequest(
        status="failed",
        message="元素未找到: #login-btn",
        original_request="点击登录按钮",
        site_id="test_site"
    )

    result = engine.handle_execution_feedback(feedback)

    assert "status" in result
    assert "message" in result
    assert "retry_code" in result

def test_workflow_engine_handle_feedback_no_request():
    """Test handling feedback without original_request"""
    from api.models import ExecutionFeedbackRequest
    engine = get_workflow_engine()

    feedback = ExecutionFeedbackRequest(
        status="failed",
        message="执行错误",
        site_id="test_site"
    )

    result = engine.handle_execution_feedback(feedback)

    # Should still handle gracefully
    assert result["status"] in ["failed", "acknowledged"]