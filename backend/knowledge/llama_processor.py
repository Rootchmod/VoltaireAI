"""
Document Processor for VoltaireAI

Processes DOM elements into documents for vector storage.
Supports category-based organization and optimization strategies.
"""

from typing import Dict, Any, List, Optional
import logging

from knowledge.strategies import DEFAULT_STRATEGY_ID

logger = logging.getLogger(__name__)


# 简单的 Document 类，替代 llama_index.Document
class SimpleDocument:
    """简单的文档对象，用于存储文本和元数据"""
    def __init__(self, text: str, metadata: Dict[str, Any], doc_id: str):
        self.text = text
        self.metadata = metadata
        self.doc_id = doc_id


class LlamaProcessor:
    """
    Processes DOM elements into structured documents.

    Converts raw DOM element data into LlamaIndex Documents
    that can be stored in ChromaDB for semantic search.
    Supports optimization strategies via OptimizationProcessor.
    """

    def process_dom_elements(self, elements: List[Dict[str, Any]]) -> List[SimpleDocument]:
        """
        Convert DOM elements to Documents.

        Args:
            elements: List of DOM element dictionaries with:
                - type: Element type (button, input, form, etc.)
                - selector: CSS selector
                - text: Visible text content
                - position: Element position on page
                - actions: Available actions (click, fill, etc.)

        Returns:
            List of Document objects
        """
        documents = []

        for i, element in enumerate(elements):
            content = self._create_element_description(element)

            metadata = {
                "element_type": element.get("type", "unknown"),
                "selector": element.get("selector", ""),
                "actions": ",".join(element.get("actions", [])),
                "position_x": element.get("position", {}).get("x", 0),
                "position_y": element.get("position", {}).get("y", 0),
                "text_content": element.get("text", ""),
                "element_id": element.get("id", f"elem_{i}")
            }

            doc = SimpleDocument(
                text=content,
                metadata=metadata,
                doc_id=metadata["element_id"]
            )

            documents.append(doc)

        logger.info(f"Processed {len(documents)} DOM elements into documents")
        return documents

    def _create_element_description(self, element: Dict[str, Any]) -> str:
        """
        Create human-readable description of element.

        Args:
            element: Element dictionary

        Returns:
            Descriptive text for semantic search
        """
        type_ = element.get("type", "element")
        selector = element.get("selector", "")
        text = element.get("text", "")
        actions = element.get("actions", [])

        description_parts = []

        if text:
            description_parts.append(f"{type_} with text '{text}'")
        else:
            description_parts.append(f"{type_} element")

        if selector:
            description_parts.append(f"located at {selector}")

        if actions:
            action_text = ", ".join(actions)
            description_parts.append(f"can perform: {action_text}")

        position = element.get("position", {})
        if position.get("x") and position.get("y"):
            description_parts.append(f"positioned at ({position['x']}, {position['y']})")

        description = " - ".join(description_parts)
        return description

    def process_and_store(
        self,
        elements: List[Dict[str, Any]],
        site_id: str = None,
        chroma_manager = None,
        category: str = "sitemap",
        name: str = "default",
        strategy_id: str = None,
    ) -> None:
        """
        Process elements and store directly in ChromaDB.

        Args:
            elements: DOM elements to process
            site_id: [deprecated] Old site_id parameter, mapped to name
            chroma_manager: ChromaManager instance
            category: Knowledge base category (table/document/sitemap)
            name: Collection name within category
            strategy_id: Optimization strategy ID (None = default)
        """
        # Backward compat: if site_id provided but no explicit category/name
        if site_id and category == "sitemap" and name == "default":
            # If an actual site_id is passed, use it as the name
            if site_id != "default":
                name = site_id

        # Process elements into documents
        documents = self.process_dom_elements(elements)

        # Convert to ChromaDB format
        chroma_elements = []
        for doc in documents:
            chroma_elements.append({
                'id': doc.doc_id,
                'content': doc.text,
                'metadata': doc.metadata
            })

        # Store in ChromaDB
        chroma_manager.add_elements(category, name, chroma_elements)
        logger.info(f"Stored {len(chroma_elements)} elements in {category}_{name}")

    def process_document_and_store(
        self,
        content: str,
        filename: str,
        chroma_manager,
        category: str = "document",
        name: str = "default",
        strategy_id: str = None,
    ) -> None:
        """
        Process a document's text content and store with optimization.

        Args:
            content: Document text content
            filename: Original filename
            chroma_manager: ChromaManager instance
            category: Knowledge base category
            name: Collection name
            strategy_id: Optimization strategy ID (None = use default)
        """
        if strategy_id is None:
            strategy_id = DEFAULT_STRATEGY_ID

        # Apply optimization strategy
        try:
            from knowledge.optimization_processor import OptimizationProcessor
            from llm.llm_client import get_llm_client
            llm_client = get_llm_client()
            opt_processor = OptimizationProcessor(llm_client)
            elements = opt_processor.process(
                content,
                strategy_id=strategy_id,
                metadata={
                    "source_file": filename,
                    "strategy": strategy_id,
                    "category": category,
                }
            )
        except Exception as e:
            logger.warning(f"Optimization processing failed: {e}, using simple chunking")
            from knowledge.optimization_processor import OptimizationProcessor
            opt_processor = OptimizationProcessor(None)  # No LLM = simple chunking
            elements = opt_processor.process(
                content,
                strategy_id="hierarchical_indices",
                metadata={"source_file": filename, "category": category}
            )

        # Store processed elements in the target collection
        chroma_manager.add_elements(category, name, elements)
        logger.info(f"Stored {len(elements)} chunks from {filename} in {category}_{name}")

    # Singleton instance
_llama_processor: Optional[LlamaProcessor] = None

def get_llama_processor() -> LlamaProcessor:
    """Get or create LlamaProcessor singleton."""
    global _llama_processor
    if _llama_processor is None:
        _llama_processor = LlamaProcessor()
    return _llama_processor