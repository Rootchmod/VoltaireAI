"""
LLM Client for VoltaireAI

Wraps LangChain LLM calls for DeepSeek API (OpenAI-compatible).
All prompt logic is driven by agent config, no hardcoded templates.
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List

from config.config_loader import load_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM client wrapper for DeepSeek API.

    Uses LangChain ChatOpenAI with custom base_url for DeepSeek.
    All generation is driven by agent configuration, not hardcoded templates.
    """

    def __init__(self):
        self.settings = load_settings()
        self.llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        """Initialize LangChain LLM from settings."""
        model_sources = self.settings.get("model_sources", [])
        default_source = self.settings.get("default_model_source", "deepseek")

        source_config = None
        for source in model_sources:
            if source.get("name") == default_source:
                source_config = source
                break

        if not source_config:
            logger.warning(f"Model source '{default_source}' not found in settings")
            return

        try:
            from langchain_openai import ChatOpenAI

            self.llm = ChatOpenAI(
                model=source_config.get("model", "deepseek-chat"),
                api_key=source_config.get("api_key", ""),
                base_url=source_config.get("base_url", "https://api.deepseek.com"),
                temperature=0.7,
                max_tokens=2000,
                timeout=30,
                max_retries=0,
            )
            logger.info(f"LLM initialized: {source_config.get('model')} at {source_config.get('base_url')}")
        except ImportError as e:
            logger.error(f"Failed to import langchain_openai: {e}")
            self.llm = None
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None

    def _reload_settings(self) -> bool:
        """Reload settings and reinitialize LLM if config changed."""
        old_settings = self.settings
        self.settings = load_settings()
        if self.settings != old_settings or self.llm is None:
            self._init_llm()
        return self.is_available()

    def is_available(self) -> bool:
        """Check if LLM is initialized."""
        return self.llm is not None

    # ── Core LLM call ──────────────────────────────────────

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call LLM with system and user prompts. Returns response text or error string.
        """
        self._reload_settings()

        if not self.is_available():
            return "LLM_ERROR: LLM服务暂不可用，请检查API配置。"

        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"LLM_ERROR: {str(e)}"

    # ── Intent Classification ──────────────────────────────

    def classify_intent(self, message: str, agent_config: Dict[str, Any]) -> str:
        """
        Classify user intent using agent-configured LLM prompt.

        Args:
            message: User message
            agent_config: Agent configuration with role and rules

        Returns:
            "operation" or "question"
        """
        system_prompt = self._build_system_prompt(agent_config)
        user_prompt = f"用户消息: {message}\n\n请判断意图类型。"

        result = self._call_llm(system_prompt, user_prompt)
        if result.startswith("LLM_ERROR:"):
            logger.warning(f"Intent classification failed: {result}")
            return "question"  # Safe default
        return result.strip().lower()

    # ── Code Generation ────────────────────────────────────

    def generate_code(
        self,
        user_request: str,
        elements: List[Dict[str, Any]],
        agent_config: Dict[str, Any],
    ) -> str:
        """
        Generate operation code using agent-configured LLM.

        Args:
            user_request: User's operation request
            elements: Relevant DOM elements from knowledge base
            agent_config: Agent configuration (role, rules)

        Returns:
            JavaScript code wrapped in ```js-start```js-end fences,
            or error message wrapped in the same fences
        """
        # All rules come from agent config (editable via admin UI)
        system_prompt = self._build_system_prompt(agent_config)

        element_context = self._build_element_context(elements)

        user_prompt = f"用户请求: {user_request}\n{element_context}\n\n请生成执行此操作的JavaScript代码。"

        result = self._call_llm(system_prompt, user_prompt)
        return self._wrap_code_response(result, user_request)

    # ── Answer Generation ──────────────────────────────────

    def generate_answer(
        self,
        user_question: str,
        elements: List[Dict[str, Any]],
        agent_config: Dict[str, Any],
    ) -> str:
        """
        Generate answer using agent-configured LLM.

        Args:
            user_question: User's question
            elements: Relevant knowledge elements
            agent_config: Agent configuration (role, rules)

        Returns:
            Answer text
        """
        system_prompt = self._build_system_prompt(agent_config)

        knowledge_context = self._build_knowledge_context(elements)

        user_prompt = f"用户问题: {user_question}\n{knowledge_context}\n\n请回答用户的问题。"

        result = self._call_llm(system_prompt, user_prompt)
        if result.startswith("LLM_ERROR:"):
            return "抱歉，AI服务暂时不可用，请稍后再试。"
        return result

    # ── Checklist Generation ────────────────────────────────

    def generate_checklist(
        self,
        user_request: str,
        elements: List[Dict[str, Any]],
        agent_config: Dict,
    ) -> dict:
        """
        Generate a multi-step checklist using agent-configured LLM.

        Args:
            user_request: User's operation request
            elements: Relevant DOM elements
            agent_config: Agent configuration

        Returns:
            Checklist dict with plan, progress, errors
        """
        self._reload_settings()

        system_prompt = (
            "你是一个网站操作规划专家。将用户请求分解为有序的执行步骤。\n"
            "返回JSON格式，不要有其他文字：\n"
            '{"plan": [{"step": 1, "description": "步骤描述", '
            '"target_element": "CSS选择器", "expected_result": "预期结果"}], '
            '"progress": {"total": 步骤总数, "completed": 0, "failed": 0}, '
            '"errors": []}'
        )

        element_context = self._build_element_context(elements)

        user_prompt = (
            f"用户请求: {user_request}\n\n"
            f"可用元素: {element_context or '无(需根据描述生成通用步骤)'}\n\n"
            "请将操作分解为具体的执行步骤。"
        )

        result = self._call_llm(system_prompt, user_prompt)

        if result.startswith("LLM_ERROR:"):
            return self._simple_checklist(user_request, elements)

        try:
            json_match = re.search(r"\{[\s\S]*\}", result)
            if json_match:
                checklist = json.loads(json_match.group())
                for item in checklist.get("plan", []):
                    item.setdefault("status", "pending")
                return checklist
        except Exception as e:
            logger.error(f"Checklist parse failed: {e}")

        return self._simple_checklist(user_request, elements)

    # ── Code Regeneration (with error context) ─────────────

    def regenerate_code_with_error(
        self,
        user_request: str,
        elements: List[Dict[str, Any]],
        error_message: str,
        agent_config: Dict[str, Any],
    ) -> str:
        """
        Regenerate code after execution failure, with error context.

        Args:
            user_request: Original user request
            elements: DOM elements
            error_message: Error from previous execution
            agent_config: Agent configuration (role, rules)

        Returns:
            Corrected JavaScript code wrapped in ```js-start```js-end fences
        """
        # All rules come from agent config; append only error context
        system_prompt = self._build_system_prompt(agent_config)
        system_prompt += (
            f"\n\n上一次执行失败，错误信息: {error_message}\n"
            "请修正代码避免同样错误。"
        )

        element_context = self._build_element_context(elements)

        user_prompt = (
            f"用户请求: {user_request}\n"
            f"可用元素: {element_context or '无'}\n"
            f"上一次错误: {error_message}\n\n"
            "请生成修正后的JavaScript代码。"
        )

        result = self._call_llm(system_prompt, user_prompt)
        return self._wrap_code_response(result, user_request)

    # ── Prompt Builders ────────────────────────────────────

    def _build_system_prompt(self, agent_config: Dict[str, Any]) -> str:
        """Build system prompt from agent configuration."""
        role = agent_config.get("role", "")
        rules = agent_config.get("rules", [])
        parts = [role]
        if rules:
            parts.append("\n规则:\n" + "\n".join(f"- {r}" for r in rules))
        return "\n".join(parts)

    def _build_element_context(self, elements: List[Dict[str, Any]]) -> str:
        """Build element context string for prompts."""
        if not elements:
            return (
                "知识库中没有找到相关页面元素。"
                "请使用Testing Library API（screen/fireEvent/waitFor）实现用户需求。"
                "例如: window.scrollTo()、history.back()、location.reload()、"
                "screen.getByText() + fireEvent.click() 等。"
                "不要告知用户找不到元素，直接生成代码。"
            )

        lines = ["可用页面元素:"]
        for elem in elements[:10]:
            metadata = elem.get("metadata", {})
            selector = metadata.get("selector", "unknown")
            elem_type = metadata.get("element_type", "unknown")
            actions = metadata.get("actions", "")
            content = elem.get("content", "")
            lines.append(f"- 类型: {elem_type}, 选择器: {selector}, 可用操作: {actions}, 描述: {content}")
        return "\n".join(lines)

    def _build_knowledge_context(self, elements: List[Dict[str, Any]]) -> str:
        """Build knowledge context string for QA prompts."""
        if not elements:
            return "注意: 知识库未返回匹配结果，请基于通用知识回答用户问题，并建议用户完善知识库。"

        lines = ["知识库信息:"]
        for elem in elements[:10]:
            content = elem.get("content", "")
            metadata = elem.get("metadata", {})
            selector = metadata.get("selector", "")
            if content:
                if selector:
                    lines.append(f"- [选择器: {selector}] {content}")
                else:
                    lines.append(f"- {content}")
        return "\n".join(lines)

    # ── LLM-based Element Selection ─────────────────────────

    def select_relevant_elements(
        self,
        query: str,
        all_elements: List[Dict[str, Any]],
        n_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to select the most relevant elements for a query.

        No rule-based filtering — LLM judges semantic relevance independently.

        Args:
            query: User query
            all_elements: All candidate elements from knowledge base
            n_results: Number of elements to select

        Returns:
            Selected elements most relevant to the query
        """
        if not all_elements:
            return []

        if len(all_elements) <= n_results:
            return all_elements

        if not self.is_available():
            # LLM unavailable: return first N (sitemap elements are often at the end,
            # document/table elements at the beginning due to collection order)
            return all_elements[:n_results]

        # Build candidate list for LLM
        candidates = []
        for i, elem in enumerate(all_elements):
            meta = elem.get("metadata", {})
            source_cat = meta.get("_source_category", meta.get("category", ""))
            elem_type = meta.get("element_type", "")
            candidates.append(
                f"[{i}] 知识库类别={source_cat}, 元素类型={elem_type}, "
                f"来源={meta.get('source_file', meta.get('selector', ''))}, "
                f"内容={elem.get('content', '')[:200]}"
            )

        system = (
            "你是知识检索专家。根据用户查询，从候选元素列表中选出最相关的元素。"
            "注意: 如果用户请求是操作类任务，优先选择知识库类别=table的元素(operation_step类型)，"
            "其次是sitemap元素(具体页面可点击元素)，最后才选document(text_chunk类型)作为参考。"
            "返回JSON格式: {\"indices\": [3, 7, 1, ...]} "
            "indices数组按相关度从高到低排列，最多返回所需数量。"
            "只返回JSON，不要其他文字。"
        )
        user = (
            f"用户查询: {query}\n\n"
            f"需要选出最相关的 {n_results} 个元素\n\n"
            f"候选元素:\n" + "\n".join(candidates)
        )

        result = self._call_llm(system, user)
        if result.startswith("LLM_ERROR:"):
            logger.warning(f"LLM selection failed: {result}, returning first {n_results}")
            return all_elements[:n_results]

        try:
            import re
            match = re.search(r"\{[\s\S]*\}", result)
            if match:
                data = json.loads(match.group())
                indices = data.get("indices", [])
                selected = [all_elements[i] for i in indices if 0 <= i < len(all_elements)]
                logger.info(f"LLM selected {len(selected)}/{len(all_elements)} elements for query: {query[:50]}")
                return selected[:n_results]
        except Exception as e:
            logger.error(f"Failed to parse LLM selection: {e}")

        return all_elements[:n_results]

    def _wrap_code_response(self, result: str, user_request: str) -> str:
        """Ensure response has proper markdown code fences, or return error."""
        if result.startswith("LLM_ERROR:"):
            error_msg = result.replace("LLM_ERROR:", "").strip()
            return (
                f"```js-start\n"
                f"console.error('AI服务不可用: {error_msg}');\n"
                f"```js-end"
            )

        # Normalize to standard markdown fence format
        result_lower = result.lower()

        # Check for new format (markdown fences)
        has_new_start = "```js-start" in result_lower
        has_new_end = "```js-end" in result_lower

        # Check for old format (HTML tags) - for backward compatibility
        has_old_start = "<js-start>" in result_lower
        has_old_end = "<js-end>" in result_lower or "</js-end>" in result_lower

        if has_new_start and has_new_end:
            # Already in new format, just normalize
            result = re.sub(r"```js-start\s*", "```js-start\n", result, flags=re.IGNORECASE)
            result = re.sub(r"\s*```js-end", "\n```js-end", result, flags=re.IGNORECASE)
        elif has_old_start and has_old_end:
            # Convert old format to new
            result = re.sub(r"<\/?js-start>", "```js-start\n", result, flags=re.IGNORECASE)
            result = re.sub(r"<\/?js-end>", "\n```js-end", result, flags=re.IGNORECASE)
        else:
            # Strip any partial tags, wrap in new format
            cleaned = re.sub(r"<\/?js-start>|<\/?js-end>|```js-start|```js-end", "", result, flags=re.IGNORECASE).strip()
            result = f"```js-start\n{cleaned}\n```js-end"

        return result

    def _simple_checklist(self, user_request: str, elements: List[Dict]) -> dict:
        """Minimal single-step checklist when LLM unavailable."""
        return {
            "plan": [
                {
                    "step": 1,
                    "description": user_request,
                    "target_element": (
                        elements[0].get("metadata", {}).get("selector", "") if elements else None
                    ),
                    "expected_result": "操作完成",
                    "status": "pending",
                }
            ],
            "progress": {"total": 1, "completed": 0, "failed": 0},
            "errors": [],
        }


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLMClient singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
