"""
Intent Classifier for VoltaireAI

Classifies user intent using LLM agent.
"""

from api.models import IntentType
from llm.llm_client import get_llm_client
from agents.agent_manager import get_agent_manager
import logging

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classifies user message intent using LLM agent.

    Uses the intent_classifier agent config to construct
    LLM prompts for intent classification.
    """

    def classify(self, message: str) -> IntentType:
        """
        Classify message intent using LLM.

        Args:
            message: User message text

        Returns:
            IntentType (OPERATION or QUESTION)
        """
        agent_manager = get_agent_manager()
        agent_config = agent_manager.get_agent_by_id("intent_classifier")

        if not agent_config:
            logger.warning("intent_classifier agent not found, defaulting to QUESTION")
            return IntentType.QUESTION

        llm_client = get_llm_client()
        result = llm_client.classify_intent(message, agent_config)

        if "operation" in result.lower():
            intent = IntentType.OPERATION
        else:
            intent = IntentType.QUESTION

        logger.info(f"Intent classified as {intent} for message: {message[:50]}")
        return intent

    def classify_with_confidence(self, message: str) -> dict:
        """
        Classify intent with confidence score.

        Args:
            message: User message

        Returns:
            dict with intent, confidence
        """
        intent = self.classify(message)
        return {
            "intent": intent,
            "confidence": 0.8,
        }


# Singleton instance
_intent_classifier: IntentClassifier = None


def get_intent_classifier() -> IntentClassifier:
    """
    Get or create IntentClassifier singleton.

    Returns:
        IntentClassifier instance
    """
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier
