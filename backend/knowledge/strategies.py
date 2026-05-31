"""
Knowledge Base Optimization Strategies

Defines available RAG optimization strategies with metadata.
Default strategy: hierarchical_indices (层次化索引, score 0.84).
"""

OPTIMIZATION_STRATEGIES = [
    {
        "id": "none",
        "name": "不优化",
        "score": 0,
        "core_idea": "不做任何处理，直接按段落/空行切分存储原文"
    },
    {
        "id": "semantic_chunking",
        "name": "语义分块",
        "score": 0.20,
        "core_idea": "按相邻句语义相似度合并Chunk，保留上下文"
    },
    {
        "id": "context_enriched_retrieval",
        "name": "上下文增强检索",
        "score": 0.60,
        "core_idea": "召回相关Chunk时一并返回其前后相邻块"
    },
    {
        "id": "contextual_headers",
        "name": "Chunk标题增强",
        "score": 0.50,
        "core_idea": "为每个Chunk用LLM生成摘要标题，标题+内容联合Embedding"
    },
    {
        "id": "document_augmentation",
        "name": "文档增强",
        "score": 0.70,
        "core_idea": "为每个Chunk预生成若干相关问题作为额外检索入口"
    },
    {
        "id": "graphrag",
        "name": "知识图谱RAG",
        "score": 0.78,
        "core_idea": "构建实体-关系图，按节点/边检索，准确率较高但构建成本高"
    },
    {
        "id": "hierarchical_indices",
        "name": "层次化索引",
        "score": 0.84,
        "core_idea": "先建摘要层(Summary)→再检索细粒度Chunk层，平衡精度与上下文完整性"
    },
    {
        "id": "hyde",
        "name": "HyDE(假设性文档嵌入)",
        "score": 0.50,
        "core_idea": "LLM先生成'假设答案'，再用其向量检索真实文档，若假设方向偏差效果降低"
    },
    {
        "id": "fusion_hybrid_search",
        "name": "融合检索",
        "score": 0.824,
        "core_idea": "语义检索+关键词(BM25)双路召回并融合排序，兼顾精确匹配与语义理解"
    },
    {
        "id": "crag",
        "name": "CRAG(纠错型RAG)",
        "score": 0.824,
        "core_idea": "对检索结果做相关性判断→高分直接用/低分配合Web搜索补充"
    },
    {
        "id": "self_rag",
        "name": "Self-RAG",
        "score": 0.60,
        "core_idea": "引入反思机制判断是否需检索、结果是否相关、答案是否被支撑"
    },
]

DEFAULT_STRATEGY_ID = "none"


def get_strategy_by_id(strategy_id: str):
    """Get strategy metadata by ID."""
    for s in OPTIMIZATION_STRATEGIES:
        if s["id"] == strategy_id:
            return s
    return None


def get_all_strategies():
    """Get all available strategies."""
    return OPTIMIZATION_STRATEGIES
