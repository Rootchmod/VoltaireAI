# backend/llm/__init__.py
"""LLM integration module for VoltaireAI"""

from llm.llm_client import get_llm_client, LLMClient

__all__ = ['get_llm_client', 'LLMClient']