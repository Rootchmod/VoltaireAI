"""
Workflow Engine for VoltaireAI

Orchestrates the execution of AI workflow steps.
"""

from typing import Dict, Any, List, Optional
from api.models import IntentType, ChatRequest, ChatResponse, ExecutionFeedbackRequest
from workflows.intent_classifier import get_intent_classifier
from agents.agent_manager import get_agent_manager
from knowledge.chroma_manager import get_chroma_manager
from knowledge.llama_processor import get_llama_processor
from llm.llm_client import get_llm_client
import logging

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """
    Executes AI workflow to process user requests.

    Main workflow:
    1. Classify intent (operation vs question)
    2. Select appropriate agent
    3. Query knowledge base if needed
    4. Generate checklist for operations
    5. Generate response/code
    6. Return to API
    """

    def __init__(self):
        """
        Initialize workflow engine with required components.
        """
        self.intent_classifier = get_intent_classifier()
        self.agent_manager = get_agent_manager()
        self.chroma_manager = get_chroma_manager()
        self.llama_processor = get_llama_processor()
        self.llm_client = get_llm_client()

    def execute_chat_workflow(self, request: ChatRequest) -> ChatResponse:
        """
        Execute main chat workflow.

        Args:
            request: ChatRequest from frontend

        Returns:
            ChatResponse with AI response
        """
        logger.info(f"Executing workflow for: {request.message}")

        # Step 1: Classify intent
        intent = self.intent_classifier.classify(request.message)

        # Step 2: Select agent
        agent_config = self.agent_manager.get_agent_by_intent(intent)
        if not agent_config:
            return ChatResponse(
                message="抱歉，我无法识别您的请求类型",
                intent=intent,
                code=None,
                checklist=None
            )

        # Step 3: Always query knowledge base across all categories
        all_elements = self.chroma_manager.query_all_categories(
            request.message,
            n_results=30
        )
        # LLM selects most relevant elements (no rule-based filtering)
        knowledge_elements = self.llm_client.select_relevant_elements(
            request.message, all_elements, n_results=10
        )

        # Step 4: Delegate to agent (LLM handles all generation)
        if intent == IntentType.OPERATION:
            code = self.llm_client.generate_code(
                user_request=request.message,
                elements=knowledge_elements,
                agent_config=agent_config,
            )
            checklist = self.llm_client.generate_checklist(
                user_request=request.message,
                elements=knowledge_elements,
                agent_config=agent_config,
            )
            return ChatResponse(
                message=f"我将执行：{request.message}",
                intent=intent,
                code=code,
                checklist=checklist,
            )
        else:
            answer = self.llm_client.generate_answer(
                user_question=request.message,
                elements=knowledge_elements,
                agent_config=agent_config,
            )
            return ChatResponse(
                message=answer,
                intent=intent,
                code=None,
                checklist=None,
            )

    def execute_chat_workflow_stream(self, message: str, site_id: str = "default"):
        """
        Execute chat workflow as a generator yielding progress events for SSE.

        Args:
            message: User message
            site_id: Site identifier

        Yields:
            Dict with progress or complete events
        """
        logger.info(f"Streaming workflow for: {message}")

        # Step 1: Classify intent
        yield {"type": "progress", "step": "intent", "message": "正在分析请求意图...", "progress": 10}
        intent = self.intent_classifier.classify(message)

        # Step 2: Select agent
        yield {"type": "progress", "step": "agent", "message": "正在选择处理Agent...", "progress": 20}
        agent_config = self.agent_manager.get_agent_by_intent(intent)
        if not agent_config:
            yield {
                "type": "complete",
                "data": {
                    "message": "抱歉，我无法识别您的请求类型",
                    "intent": intent.value if hasattr(intent, 'value') else str(intent),
                    "code": None,
                    "checklist": None
                }
            }
            return

        # Step 3: Always query knowledge base across all categories
        yield {"type": "progress", "step": "knowledge", "message": "正在查询知识库...", "progress": 40}
        all_elements = self.chroma_manager.query_all_categories(
            message, n_results=30
        )
        # LLM selects most relevant elements (no rule-based filtering)
        knowledge_elements = self.llm_client.select_relevant_elements(
            message, all_elements, n_results=10
        )

        # Step 4: Delegate to agent (LLM handles all generation)
        yield {"type": "progress", "step": "generating", "message": "AI正在生成回复...", "progress": 60}

        if intent == IntentType.OPERATION:
            code = self.llm_client.generate_code(
                user_request=message,
                elements=knowledge_elements,
                agent_config=agent_config,
            )
            checklist = self.llm_client.generate_checklist(
                user_request=message,
                elements=knowledge_elements,
                agent_config=agent_config,
            )
            yield {
                "type": "complete",
                "data": {
                    "message": f"我将执行：{message}",
                    "intent": "operation",
                    "code": code,
                    "checklist": checklist,
                },
            }
        else:
            answer = self.llm_client.generate_answer(
                user_question=message,
                elements=knowledge_elements,
                agent_config=agent_config,
            )
            yield {
                "type": "complete",
                "data": {
                    "message": answer,
                    "intent": "question",
                    "code": None,
                    "checklist": None,
                },
            }

    def handle_execution_feedback(self, feedback: ExecutionFeedbackRequest) -> Dict[str, Any]:
        """
        Handle execution feedback from frontend.

        Args:
            feedback: ExecutionFeedbackRequest from frontend

        Returns:
            Dict with next action info
        """
        logger.info(f"Execution feedback: {feedback.status} - {feedback.message}")

        if feedback.status == "success":
            return {
                "status": "acknowledged",
                "message": "操作执行成功",
                "next_action": "continue",
                "retry_code": None
            }

        # Failure - try to regenerate code
        if feedback.original_request:
            agent_config = self.agent_manager.get_agent_by_id("operation_agent")
            if not agent_config:
                agent_config = self.agent_manager.get_agent_by_intent(IntentType.OPERATION)

            if agent_config:
                all_elements = self.chroma_manager.query_all_categories(
                    feedback.original_request,
                    n_results=30
                )
                knowledge_elements = self.llm_client.select_relevant_elements(
                    feedback.original_request, all_elements, n_results=10
                )

                new_code = self.llm_client.regenerate_code_with_error(
                    user_request=feedback.original_request,
                    elements=knowledge_elements,
                    error_message=feedback.message,
                    agent_config=agent_config,
                )

                return {
                    "status": "retry",
                    "message": f"执行失败，已重新生成代码: {feedback.message}",
                    "next_action": "retry",
                    "retry_code": new_code
                }

        return {
            "status": "failed",
            "message": f"操作失败: {feedback.message}",
            "next_action": "abort",
            "retry_code": None
        }



# Singleton instance
_workflow_engine: WorkflowEngine = None

def get_workflow_engine() -> WorkflowEngine:
    """
    Get or create WorkflowEngine singleton.

    Returns:
        WorkflowEngine instance
    """
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
