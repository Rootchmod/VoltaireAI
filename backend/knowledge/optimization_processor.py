"""
Optimization Processor for VoltaireAI Knowledge Base

Applies RAG optimization strategies to uploaded content using LLM-based
sub-agents (not rule-based processing). Supports parallel sub-agent
spawning for large documents.

Default strategy: hierarchical_indices (层次化索引, score 0.84).
"""

import concurrent.futures
import json
import logging
import re
from typing import Dict, Any, List, Optional

from knowledge.strategies import (
    OPTIMIZATION_STRATEGIES,
    DEFAULT_STRATEGY_ID,
    get_strategy_by_id,
)

logger = logging.getLogger(__name__)

# Batch size for splitting content across sub-agents
SUB_AGENT_BATCH_SIZE = 3000  # characters per sub-agent


class OptimizationProcessor:
    """
    Applies optimization strategies to knowledge base content using LLM agents.

    Each strategy uses LLM calls to process content — no rule-based logic.
    Large content is split into batches and processed by parallel sub-agents.
    """

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLMClient instance for making LLM calls.
                        If None, processing is skipped (pass-through).
        """
        self.llm_client = llm_client

    # ── Main Entry ──────────────────────────────────────────

    def process(
        self,
        content: str,
        strategy_id: str = DEFAULT_STRATEGY_ID,
        metadata: dict = None,
    ) -> List[Dict[str, Any]]:
        """
        Process content using the specified optimization strategy.

        Args:
            content: Raw text content to process
            strategy_id: Strategy ID from OPTIMIZATION_STRATEGIES
            metadata: Additional metadata for the elements

        Returns:
            List of element dicts with id, content, metadata
        """
        strategy = get_strategy_by_id(strategy_id)
        if strategy is None:
            logger.warning(f"Unknown strategy '{strategy_id}', using default")
            strategy = get_strategy_by_id(DEFAULT_STRATEGY_ID)

        if strategy_id == "none" or not self.llm_client or not self.llm_client.is_available():
            if strategy_id == "none":
                logger.info("Strategy 'none' selected, using simple chunking without LLM")
            else:
                logger.warning("LLM unavailable, using simple chunking fallback")
            return self._simple_chunk(content, metadata or {})

        logger.info(f"Processing with strategy: {strategy['name']} ({strategy_id})")

        # Large content -> split into batches for parallel sub-agent processing
        if len(content) > SUB_AGENT_BATCH_SIZE:
            return self._process_with_sub_agents(content, strategy, metadata or {})
        else:
            return self._process_single(content, strategy, metadata or {})

    # ── Sub-Agent Parallel Processing ───────────────────────

    def _process_with_sub_agents(
        self,
        content: str,
        strategy: dict,
        metadata: dict,
        max_workers: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Split content into batches and process each with a sub-agent (parallel LLM calls).

        Args:
            content: Full text content
            strategy: Strategy metadata dict
            metadata: Element metadata
            max_workers: Max parallel sub-agents

        Returns:
            Combined list of element dicts
        """
        batches = self._split_into_batches(content, SUB_AGENT_BATCH_SIZE)
        logger.info(f"Split content into {len(batches)} batches, processing with up to {max_workers} sub-agents")

        all_elements = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._process_single, batch, strategy, metadata): i
                for i, batch in enumerate(batches)
            }
            for future in concurrent.futures.as_completed(futures):
                batch_idx = futures[future]
                try:
                    elements = future.result()
                    # Adjust IDs to avoid collisions across batches
                    for elem in elements:
                        elem["id"] = f"{elem['id']}_b{batch_idx}"
                    all_elements.extend(elements)
                except Exception as e:
                    logger.error(f"Sub-agent batch {batch_idx} failed: {e}")
                    # Fallback: simple chunk for this batch
                    batch_meta = {**metadata, "batch": batch_idx}
                    all_elements.extend(self._simple_chunk(batches[batch_idx], batch_meta))

        return all_elements

    @staticmethod
    def _split_into_batches(content: str, batch_size: int) -> List[str]:
        """Split content into batches, trying to break at paragraph boundaries."""
        paragraphs = content.split("\n\n")
        batches = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > batch_size and current:
                batches.append(current.strip())
                current = para
            else:
                current += "\n\n" + para if current else para
        if current.strip():
            batches.append(current.strip())
        return batches or [content]

    # ── Single-Batch Processing ─────────────────────────────

    def _process_single(
        self,
        content: str,
        strategy: dict,
        metadata: dict,
    ) -> List[Dict[str, Any]]:
        """
        Process a single batch of content with the given strategy.

        All strategy methods use LLM calls, not rule-based logic.
        """
        strategy_id = strategy["id"]
        method_name = f"_strategy_{strategy_id}"
        method = getattr(self, method_name, None)

        if method is None:
            logger.warning(f"No method for strategy '{strategy_id}', using simple chunk")
            return self._simple_chunk(content, metadata)

        try:
            return method(content, metadata)
        except Exception as e:
            logger.error(f"Strategy {strategy_id} failed: {e}, falling back to simple chunk")
            return self._simple_chunk(content, metadata)

    # ── Strategy Implementations (all LLM-based) ────────────

    def _call_sub_agent(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM sub-agent and return response text."""
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = self.llm_client.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Sub-agent call failed: {e}")
            raise

    def _parse_json_response(self, text: str) -> dict:
        """Extract JSON object from LLM response."""
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        return {}

    def _strategy_semantic_chunking(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM splits content at semantic boundaries."""
        system = "你是文档分块专家。将以下内容按语义边界拆分为多个Chunk，每个Chunk保持上下文完整。返回JSON: {\"chunks\": [\"chunk1\", \"chunk2\", ...]}"
        response = self._call_sub_agent(system, f"内容:\n{content[:5000]}")
        data = self._parse_json_response(response)
        chunks = data.get("chunks", [content])
        return self._chunks_to_elements(chunks, metadata)

    def _strategy_context_enriched_retrieval(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM chunks content and identifies adjacency relationships."""
        system = "你是文档分析专家。将内容分块，并为每个块标注其前后相邻块的ID关系。返回JSON: {\"chunks\": [{\"id\": \"c0\", \"text\": \"...\", \"prev\": null, \"next\": \"c1\"}, ...]}"
        response = self._call_sub_agent(system, f"内容:\n{content[:5000]}")
        data = self._parse_json_response(response)
        chunks = data.get("chunks", [])
        elements = []
        for i, ch in enumerate(chunks):
            text = ch.get("text", "") if isinstance(ch, dict) else ch
            ch_meta = {**metadata, "chunk_index": i}
            if isinstance(ch, dict):
                ch_meta["prev_chunk"] = ch.get("prev")
                ch_meta["next_chunk"] = ch.get("next")
            elements.append({"id": f"ctx_{i}", "content": text, "metadata": ch_meta})
        return elements or self._simple_chunk(content, metadata)

    def _strategy_contextual_headers(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM generates descriptive headers for each chunk."""
        system = "你是文档结构化专家。将以下内容分块，为每个Chunk生成一个摘要标题。返回JSON: {\"chunks\": [{\"header\": \"标题\", \"text\": \"内容\"}, ...]}"
        response = self._call_sub_agent(system, f"内容:\n{content[:5000]}")
        data = self._parse_json_response(response)
        chunks = data.get("chunks", [])
        elements = []
        for i, ch in enumerate(chunks):
            header = ch.get("header", "") if isinstance(ch, dict) else ""
            text = ch.get("text", "") if isinstance(ch, dict) else ch
            combined = f"[{header}] {text}" if header else text
            ch_meta = {**metadata, "header": header, "chunk_index": i}
            elements.append({"id": f"hdr_{i}", "content": combined, "metadata": ch_meta})
        return elements or self._simple_chunk(content, metadata)

    def _strategy_document_augmentation(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM generates related questions for each chunk as additional retrieval entries."""
        system = "你是知识图谱专家。将内容分块，并为每个Chunk生成3-5个相关问题(作为检索入口)。返回JSON: {\"chunks\": [{\"text\": \"原内容\", \"questions\": [\"问题1\", \"问题2\"]}, ...]}"
        response = self._call_sub_agent(system, f"内容:\n{content[:5000]}")
        data = self._parse_json_response(response)
        chunks = data.get("chunks", [])
        elements = []
        for i, ch in enumerate(chunks):
            text = ch.get("text", "") if isinstance(ch, dict) else ch
            questions = ch.get("questions", []) if isinstance(ch, dict) else []
            aug_content = text + "\n\n相关问题:\n" + "\n".join(f"- {q}" for q in questions)
            ch_meta = {**metadata, "chunk_index": i, "questions": questions}
            elements.append({"id": f"aug_{i}", "content": aug_content, "metadata": ch_meta})
        return elements or self._simple_chunk(content, metadata)

    def _strategy_graphrag(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM builds entity-relationship graph and creates node/edge based elements."""
        system = "你是知识图谱构建专家。从内容中提取实体和关系，构建一个知识图谱。返回JSON: {\"entities\": [{\"id\": \"e0\", \"name\": \"实体名\", \"type\": \"类型\"}], \"relations\": [{\"from\": \"e0\", \"to\": \"e1\", \"relation\": \"关系\"}], \"chunks\": [{\"text\": \"文本\", \"entities\": [\"e0\"]}]}"
        response = self._call_sub_agent(system, f"内容:\n{content[:5000]}")
        data = self._parse_json_response(response)
        chunks = data.get("chunks", [])
        elements = []
        for i, ch in enumerate(chunks):
            text = ch.get("text", "") if isinstance(ch, dict) else ch
            ch_meta = {**metadata, "chunk_index": i}
            if isinstance(ch, dict):
                ch_meta["graph_entities"] = ch.get("entities", [])
                ch_meta["graph_type"] = "graphrag"
            elements.append({"id": f"gr_{i}", "content": text, "metadata": ch_meta})
        return elements or self._simple_chunk(content, metadata)

    def _strategy_hierarchical_indices(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM builds summary layer first, then links to detailed chunks (default strategy)."""
        # Step 1: Generate summary
        sum_system = "你是文档摘要专家。为以下内容生成一个结构化摘要(200-500字)，概括所有关键信息。只返回摘要文本，不要其他格式。"
        summary = self._call_sub_agent(sum_system, f"内容:\n{content[:5000]}")
        summary = summary.strip()

        # Step 2: Generate detailed chunks
        chunk_system = "你是文档结构化专家。将以下内容拆分为3-8个细粒度Chunk，每个Chunk包含具体细节。返回JSON: {\"chunks\": [\"chunk1\", \"chunk2\", ...]}"
        chunk_response = self._call_sub_agent(chunk_system, f"内容:\n{content[:5000]}")
        chunk_data = self._parse_json_response(chunk_response)
        chunks = chunk_data.get("chunks", [content])

        elements = []
        # Summary element (high-level index)
        elements.append({
            "id": f"hi_summary_0",
            "content": summary,
            "metadata": {**metadata, "layer": "summary", "is_summary": True, "chunk_count": len(chunks)}
        })
        # Detail chunks with link to summary
        for i, ch in enumerate(chunks):
            text = ch if isinstance(ch, str) else ch.get("text", str(ch))
            elements.append({
                "id": f"hi_detail_{i}",
                "content": text,
                "metadata": {**metadata, "layer": "detail", "summary_ref": "hi_summary_0", "chunk_index": i}
            })

        return elements

    def _strategy_hyde(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM generates hypothetical answers for retrieval alignment."""
        system = "你是问答生成专家。基于以下内容，生成5个'假设性问答对'（假设用户会问什么、答案是什么）。返回JSON: {\"qa_pairs\": [{\"question\": \"问题\", \"answer\": \"答案\"}, ...], \"chunks\": [\"原始内容分块\"]}"
        response = self._call_sub_agent(system, f"内容:\n{content[:5000]}")
        data = self._parse_json_response(response)
        chunks = data.get("chunks", [content])
        qa_pairs = data.get("qa_pairs", [])
        elements = []
        for i, ch in enumerate(chunks):
            text = ch if isinstance(ch, str) else ch.get("text", str(ch))
            # Attach most relevant QA pair
            ch_meta = {**metadata, "chunk_index": i, "hyde_qa": qa_pairs[i] if i < len(qa_pairs) else None}
            elements.append({"id": f"hyde_{i}", "content": text, "metadata": ch_meta})
        return elements or self._simple_chunk(content, metadata)

    def _strategy_fusion_hybrid_search(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM generates both semantic and keyword-based representations."""
        system = "你是搜索优化专家。将内容分块，为每个Chunk同时生成：1)语义描述 2)关键词列表 3)原始内容。返回JSON: {\"chunks\": [{\"text\": \"原始\", \"semantic\": \"语义描述\", \"keywords\": [\"kw1\", \"kw2\"]}]}"
        response = self._call_sub_agent(system, f"内容:\n{content[:5000]}")
        data = self._parse_json_response(response)
        chunks = data.get("chunks", [])
        elements = []
        for i, ch in enumerate(chunks):
            text = ch.get("text", "") if isinstance(ch, dict) else ch
            semantic = ch.get("semantic", "") if isinstance(ch, dict) else ""
            keywords = ch.get("keywords", []) if isinstance(ch, dict) else []
            combined = f"{semantic}\n\n{text}\n\n关键词: {', '.join(keywords)}"
            ch_meta = {**metadata, "chunk_index": i, "keywords": keywords, "has_semantic": bool(semantic)}
            elements.append({"id": f"fus_{i}", "content": combined, "metadata": ch_meta})
        return elements or self._simple_chunk(content, metadata)

    def _strategy_crag(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM evaluates each chunk's relevance and flags low-relevance for supplementation."""
        system = "你是检索质量评估专家。将内容分块，为每个Chunk评估检索相关性(high/medium/low)，低相关的标注需要外部补充的方向。返回JSON: {\"chunks\": [{\"text\": \"内容\", \"relevance\": \"high|medium|low\", \"supplement_hint\": \"补充方向\"}]}"
        response = self._call_sub_agent(system, f"内容:\n{content[:5000]}")
        data = self._parse_json_response(response)
        chunks = data.get("chunks", [])
        elements = []
        for i, ch in enumerate(chunks):
            text = ch.get("text", "") if isinstance(ch, dict) else ch
            relevance = ch.get("relevance", "medium") if isinstance(ch, dict) else "medium"
            hint = ch.get("supplement_hint", "") if isinstance(ch, dict) else ""
            ch_meta = {**metadata, "chunk_index": i, "relevance": relevance, "supplement_hint": hint}
            elements.append({"id": f"crag_{i}", "content": text, "metadata": ch_meta})
        return elements or self._simple_chunk(content, metadata)

    def _strategy_self_rag(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """LLM adds reflection markers for retrieval/answer verification."""
        system = "你是自省型RAG专家。将内容分块，为每个Chunk添加：1)是否需要检索此块的判断 2)此块能支撑哪些类型的问题 3)内容置信度评估。返回JSON: {\"chunks\": [{\"text\": \"内容\", \"needs_retrieval\": true, \"supports\": [\"问题类型\"], \"confidence\": 0.9}]}"
        response = self._call_sub_agent(system, f"内容:\n{content[:5000]}")
        data = self._parse_json_response(response)
        chunks = data.get("chunks", [])
        elements = []
        for i, ch in enumerate(chunks):
            text = ch.get("text", "") if isinstance(ch, dict) else ch
            ch_meta = {**metadata, "chunk_index": i}
            if isinstance(ch, dict):
                ch_meta["needs_retrieval"] = ch.get("needs_retrieval", True)
                ch_meta["supports"] = ch.get("supports", [])
                ch_meta["confidence"] = ch.get("confidence", 0.5)
            elements.append({"id": f"sr_{i}", "content": text, "metadata": ch_meta})
        return elements or self._simple_chunk(content, metadata)

    # ── Fallback ─────────────────────────────────────────────

    def _simple_chunk(self, content: str, metadata: dict) -> List[Dict[str, Any]]:
        """Simple paragraph-based chunking (fallback when LLM unavailable)."""
        paragraphs = content.split("\n\n")
        elements = []
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue
            elements.append({
                "id": f"chunk_{i}",
                "content": para,
                "metadata": {**metadata, "chunk_index": i, "strategy": "simple"}
            })
        if not elements:
            elements.append({
                "id": "chunk_0",
                "content": content,
                "metadata": {**metadata, "strategy": "simple"}
            })
        return elements

    @staticmethod
    def _chunks_to_elements(chunks: list, metadata: dict) -> List[Dict[str, Any]]:
        """Convert string chunks to element dicts."""
        elements = []
        for i, ch in enumerate(chunks):
            text = ch if isinstance(ch, str) else ch.get("text", str(ch))
            elements.append({
                "id": f"sc_{i}",
                "content": text,
                "metadata": {**metadata, "chunk_index": i}
            })
        return elements
