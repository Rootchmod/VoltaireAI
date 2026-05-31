"""
ChromaDB Manager for VoltaireAI

Manages vector storage of website operation maps.
Collections are organized by category (table/document/sitemap) + name.
Each category has a "default" system collection that cannot be deleted.

Persistence: Uses ChromaDB PersistentClient when available,
with JSON file fallback for environments where ChromaDB can't initialize.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Collection naming: {category}_{name}
SYSTEM_DEFAULT_NAMES = {"table_default", "document_default", "sitemap_default"}
CATEGORIES = {"table", "document", "sitemap"}

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except RuntimeError as e:
    if "sqlite3" in str(e):
        logger.warning("ChromaDB unavailable due to sqlite version. Using fallback.")
        CHROMADB_AVAILABLE = False
    else:
        raise
except ImportError:
    logger.warning("ChromaDB not installed. Using fallback.")
    CHROMADB_AVAILABLE = False


def _make_collection_name(category: str, name: str) -> str:
    """Build collection name from category and name."""
    return f"{category}_{name}"


def _parse_collection_name(collection_name: str) -> Optional[Tuple[str, str]]:
    """Parse category and name from collection name. Returns None if invalid."""
    for cat in CATEGORIES:
        prefix = f"{cat}_"
        if collection_name.startswith(prefix):
            return cat, collection_name[len(prefix):]
    return None


def _is_default_collection(collection_name: str) -> bool:
    """Check if a collection name is a system default collection."""
    return collection_name in SYSTEM_DEFAULT_NAMES


class ChromaManager:
    """
    Manages ChromaDB collections for website knowledge storage.

    Collections are organized by category + name:
    - sitemap_default: system default sitemap (buttons, inputs, etc.)
    - table_default: system default table (operation guides)
    - document_default: system default document (operation documents)
    - {category}_{custom_name}: user-created collections

    Falls back to JSON-persisted in-memory storage if ChromaDB unavailable.
    """

    def __init__(self, persist_dir: str = ".chroma", json_path: str = ".voltaire_knowledge/knowledge_store.json"):
        """
        Initialize ChromaDB client.

        Args:
            persist_dir: Directory to store ChromaDB data
            json_path: JSON file path for fallback persistence
        """
        self.json_path = json_path
        self.memory_store: Dict[str, dict] = {}  # Fallback: in-memory + JSON persisted
        self.collections: Dict[str, Any] = {}
        self.client = None

        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available - using JSON-persisted memory fallback")
            self._load_from_disk()
        else:
            try:
                self.client = chromadb.PersistentClient(path=persist_dir)
                logger.info(f"ChromaDB initialized at {persist_dir}")
                self._load_from_disk()  # Also load JSON as backup
                self._migrate_collection_names()
            except Exception as e:
                logger.warning(f"ChromaDB init failed: {e}. Using JSON-persisted memory fallback.")
                self.client = None
                self._load_from_disk()

    # ── JSON Persistence ────────────────────────────────────

    def _ensure_json_dir(self) -> None:
        """Create directory for JSON store if needed."""
        d = os.path.dirname(self.json_path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def _load_from_disk(self) -> None:
        """Load memory store from JSON file."""
        if not os.path.exists(self.json_path):
            logger.info(f"No existing knowledge store at {self.json_path}, starting fresh.")
            # Create default collections
            self._ensure_defaults_exist()
            return
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.memory_store = data
            # Also update the legacy collections dict for API compat
            for cname, cdata in data.items():
                self.collections[cname] = cdata
            logger.info(f"Loaded {len(data)} collections from {self.json_path}")
            self._ensure_defaults_exist()
        except Exception as e:
            logger.error(f"Failed to load knowledge store: {e}")
            self.memory_store = {}
            self._ensure_defaults_exist()

    def _save_to_disk(self) -> None:
        """Save memory store to JSON file."""
        self._ensure_json_dir()
        try:
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self.memory_store, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(self.memory_store)} collections to {self.json_path}")
        except Exception as e:
            logger.error(f"Failed to save knowledge store: {e}")

    def _ensure_defaults_exist(self) -> None:
        """Create default collections if they don't exist."""
        for default_name in SYSTEM_DEFAULT_NAMES:
            parsed = _parse_collection_name(default_name)
            if parsed and default_name not in self.memory_store:
                cat, name = parsed
                if not CHROMADB_AVAILABLE or self.client is None:
                    self.memory_store[default_name] = {
                        "elements": [],
                        "metadata": {"category": cat, "name": name, "is_default": True, "description": ""}
                    }
                    self.collections[default_name] = self.memory_store[default_name]
                    logger.info(f"Created default memory collection: {default_name}")
                else:
                    try:
                        existing = self.client.get_collection(name=default_name)
                    except Exception:
                        existing = None
                    if existing is None:
                        self.client.create_collection(
                            name=default_name,
                            metadata={"category": cat, "name": name, "is_default": True, "description": ""}
                        )
                        logger.info(f"Created default ChromaDB collection: {default_name}")
        self._save_to_disk()

    # ── Migration ───────────────────────────────────────────

    def _migrate_collection_names(self) -> None:
        """Migrate old site_xxx collections to table_migrated_site_xxx."""
        if self.client is None:
            # Memory mode migration
            migrated = []
            for cname in list(self.memory_store.keys()):
                if cname.startswith("site_") and _parse_collection_name(cname) is None:
                    new_name = f"table_migrated_{cname}"
                    self.memory_store[new_name] = self.memory_store.pop(cname)
                    self.memory_store[new_name].setdefault("metadata", {})
                    self.memory_store[new_name]["metadata"]["category"] = "table"
                    self.memory_store[new_name]["metadata"]["name"] = f"migrated_{cname}"
                    if cname in self.collections:
                        self.collections[new_name] = self.memory_store[new_name]
                        del self.collections[cname]
                    migrated.append(f"{cname} -> {new_name}")
            if migrated:
                logger.info(f"Migrated memory collections: {migrated}")
                self._save_to_disk()
            return

        # ChromaDB mode migration
        try:
            all_cols = self.client.list_collections()
            for col in all_cols:
                old_name = col.name
                if old_name.startswith("site_") and _parse_collection_name(old_name) is None:
                    new_name = f"table_migrated_{old_name}"
                    try:
                        self.client.delete_collection(name=new_name)
                    except Exception:
                        pass
                    # Cannot rename in ChromaDB directly; recreate with new name
                    old_col = self.client.get_collection(name=old_name)
                    data = old_col.get()
                    new_col = self.client.create_collection(
                        name=new_name,
                        metadata={"category": "table", "name": f"migrated_{old_name}", "is_default": False}
                    )
                    ids = data.get("ids", [])
                    if ids:
                        new_col.add(
                            ids=ids,
                            documents=data.get("documents", []),
                            metadatas=data.get("metadatas", [])
                        )
                    self.client.delete_collection(name=old_name)
                    logger.info(f"Migrated ChromaDB collection: {old_name} -> {new_name}")
        except Exception as e:
            logger.error(f"Migration failed: {e}")

    # ── Collection Management ───────────────────────────────

    def create_collection(self, category: str, name: str, description: str = "") -> Any:
        """
        Create a new collection.

        Args:
            category: One of 'table', 'document', 'sitemap'
            name: Collection name (e.g. 'default', 'my_guide')
            description: Human-readable description for AI identification

        Returns:
            ChromaDB collection object or memory dict
        """
        collection_name = _make_collection_name(category, name)

        if not CHROMADB_AVAILABLE or self.client is None:
            self.memory_store[collection_name] = {
                "elements": [],
                "metadata": {"category": category, "name": name, "is_default": _is_default_collection(collection_name), "description": description}
            }
            self.collections[collection_name] = self.memory_store[collection_name]
            logger.info(f"Created memory collection: {collection_name}")
            self._save_to_disk()
            return self.memory_store[collection_name]

        try:
            collection = self.client.create_collection(
                name=collection_name,
                metadata={
                    "category": category,
                    "name": name,
                    "is_default": _is_default_collection(collection_name),
                    "description": description,
                }
            )
            logger.info(f"Created collection: {collection_name}")
            return collection
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise

    def get_collection(self, category: str, name: str) -> Optional[Any]:
        """
        Get existing collection by category and name.

        Args:
            category: One of 'table', 'document', 'sitemap'
            name: Collection name

        Returns:
            Collection object or None if not exists
        """
        collection_name = _make_collection_name(category, name)

        if not CHROMADB_AVAILABLE or self.client is None:
            return self.memory_store.get(collection_name)

        try:
            return self.client.get_collection(name=collection_name)
        except Exception:
            return None

    def _get_collection_by_fullname(self, collection_name: str) -> Optional[Any]:
        """Get collection by its full name."""
        if not CHROMADB_AVAILABLE or self.client is None:
            return self.memory_store.get(collection_name)
        try:
            return self.client.get_collection(name=collection_name)
        except Exception:
            return None

    # ── Element Operations ──────────────────────────────────

    def add_elements(self, category: str, name: str, elements: List[Dict[str, Any]]) -> None:
        """
        Add elements to a collection.

        Args:
            category: Collection category
            name: Collection name
            elements: List of dicts with id, content, metadata
        """
        collection = self.get_collection(category, name)
        if not collection:
            collection = self.create_collection(category, name)

        collection_name = _make_collection_name(category, name)

        if not CHROMADB_AVAILABLE or self.client is None:
            for elem in elements:
                collection["elements"].append({
                    'id': elem['id'],
                    'content': elem['content'],
                    'metadata': elem.get('metadata', {})
                })
            logger.info(f"Added {len(elements)} elements to memory {collection_name}")
            self._save_to_disk()
            return

        ids = [elem['id'] for elem in elements]
        documents = [elem['content'] for elem in elements]
        metadatas = [elem.get('metadata', {}) for elem in elements]

        try:
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            logger.info(f"Added {len(elements)} elements to {collection_name}")
        except Exception as e:
            logger.error(f"Failed to add elements: {e}")
            raise

    def delete_element(self, collection_name: str, element_id: str) -> bool:
        """
        Delete a single element from a collection.

        Args:
            collection_name: Full collection name (e.g. 'table_default')
            element_id: ID of element to delete

        Returns:
            True if deleted, False if not found
        """
        if not CHROMADB_AVAILABLE or self.client is None:
            col = self.memory_store.get(collection_name)
            if not col:
                return False
            before = len(col["elements"])
            col["elements"] = [e for e in col["elements"] if e["id"] != element_id]
            if len(col["elements"]) < before:
                logger.info(f"Deleted element {element_id} from memory {collection_name}")
                self._save_to_disk()
                return True
            return False

        try:
            collection = self.client.get_collection(name=collection_name)
            collection.delete(ids=[element_id])
            logger.info(f"Deleted element {element_id} from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete element {element_id}: {e}")
            return False

    def update_element(self, collection_name: str, element_id: str, content: str = None, metadata: dict = None) -> bool:
        """
        Update a single element in a collection.

        Args:
            collection_name: Full collection name
            element_id: ID of element to update
            content: New content (or None to keep)
            metadata: New metadata (or None to keep)

        Returns:
            True if updated, False if not found
        """
        if not CHROMADB_AVAILABLE or self.client is None:
            col = self.memory_store.get(collection_name)
            if not col:
                return False
            for elem in col["elements"]:
                if elem["id"] == element_id:
                    if content is not None:
                        elem["content"] = content
                    if metadata is not None:
                        elem["metadata"] = metadata
                    logger.info(f"Updated element {element_id} in memory {collection_name}")
                    self._save_to_disk()
                    return True
            return False

        try:
            collection = self.client.get_collection(name=collection_name)
            update_kwargs = {"ids": [element_id]}
            if content is not None:
                update_kwargs["documents"] = [content]
            if metadata is not None:
                update_kwargs["metadatas"] = [metadata]
            collection.update(**update_kwargs)
            logger.info(f"Updated element {element_id} in {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update element {element_id}: {e}")
            return False

    # ── Query ───────────────────────────────────────────────

    def query_elements(
        self,
        category: str,
        name: str,
        query: str,
        n_results: int = 5,
        keywords: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query elements by semantic search within a collection.

        In memory mode, uses keyword-based scoring for semantic matching
        when keywords are provided (decomposed by LLM). Falls back to
        ChromaDB vector search when available.

        Args:
            category: Collection category
            name: Collection name
            query: Search query
            n_results: Number of results
            keywords: Pre-decomposed keywords for memory-mode matching

        Returns:
            List of matching elements
        """
        collection = self.get_collection(category, name)
        if not collection:
            logger.warning(f"Collection {category}_{name} not found")
            return []

        collection_name = _make_collection_name(category, name)

        if not CHROMADB_AVAILABLE or self.client is None:
            # Memory mode: use keyword scoring for semantic matching
            matches = list(collection["elements"])
            for item in matches:
                item["metadata"]["_source_category"] = category

            if keywords:
                # Score each element by keyword matches in content and metadata
                scored = []
                query_lower = query.lower()
                for item in matches:
                    content = (item.get("content", "") or "").lower()
                    meta = item.get("metadata", {})
                    meta_text = " ".join(str(v) for v in meta.values() if isinstance(v, str)).lower()
                    combined = content + " " + meta_text

                    score = 0
                    for kw in keywords:
                        kw_lower = kw.lower()
                        # Full keyword match in content
                        count = combined.count(kw_lower)
                        score += count * 10
                        # Partial match (keyword contains query terms)
                        for qterm in query_lower.split():
                            if qterm in kw_lower and qterm in content:
                                score += 2
                    # Bonus for matching the full original query
                    for qterm in query_lower.split():
                        if len(qterm) >= 2 and qterm in content:
                            score += 1

                    if score > 0:
                        scored.append((score, item))

                scored.sort(key=lambda x: x[0], reverse=True)
                results = [item for _, item in scored[:n_results]]
            else:
                # No keywords available: return first N (better than nothing,
                # downstream LLM handles final relevance selection)
                results = matches[:n_results]

            logger.info(
                f"Memory query '{query[:50]}' in {collection_name}: "
                f"returning {len(results)} of {len(matches)} elements"
                + (f" (keywords: {keywords[:5]})" if keywords else "")
            )
            return results

        try:
            results = collection.query(query_texts=[query], n_results=n_results)
            elements = []
            for i, doc in enumerate(results['documents'][0]):
                meta = dict(results['metadatas'][0][i]) if results['metadatas'][0][i] else {}
                meta["_source_category"] = category
                elements.append({
                    'id': results['ids'][0][i],
                    'content': doc,
                    'metadata': meta,
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
            logger.info(f"Query '{query}' in {collection_name} returned {len(elements)}")
            return elements
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def _decompose_keywords(self, query: str) -> List[str]:
        """Use LLM to decompose a query into search keywords for memory-mode matching."""
        try:
            from llm.llm_client import get_llm_client
            llm = get_llm_client()
            if not llm.is_available():
                return []
            system = "你是搜索关键词提取专家。将用户查询分解为多个独立关键词，用于文本匹配搜索。返回JSON: {\"keywords\": [\"词1\", \"词2\", ...]}。包含同义词和核心概念词。只返回JSON。"
            text = llm._call_llm(system, query[:200])
            if text.startswith("LLM_ERROR:"):
                return []
            import re
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                data = json.loads(match.group())
                return data.get("keywords", [])
        except Exception as e:
            logger.warning(f"Keyword decomposition failed: {e}")
        return []

    def query_all_categories(
        self,
        query: str,
        n_results: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Query across all categories and collections with fair distribution.

        Ensures each category (table/document/sitemap) gets representation.
        In memory mode, uses LLM-decomposed keywords for semantic matching
        instead of returning arbitrary elements.

        Args:
            query: Search query
            n_results: Max total results

        Returns:
            Interleaved list of matching elements from all collections
        """
        collections = self.list_collections()
        if not collections:
            return []

        # Decompose query into keywords for memory-mode semantic search
        keywords = self._decompose_keywords(query)

        # Give each collection a fair slice of the budget
        per_col = max(10, n_results // max(len(collections), 1))

        # Gather results grouped by category
        cat_results = {}
        for col_info in collections:
            results = self.query_elements(
                col_info["category"], col_info["display_name"], query,
                n_results=per_col, keywords=keywords
            )
            if results:
                cat = col_info["category"]
                if cat not in cat_results:
                    cat_results[cat] = []
                cat_results[cat].extend(results)

        # Interleave results from different categories so no single
        # category dominates the available slots
        all_results = []
        max_len = max((len(v) for v in cat_results.values()), default=0)
        for i in range(max_len):
            for cat in cat_results:
                if i < len(cat_results[cat]):
                    all_results.append(cat_results[cat][i])

        logger.info(
            f"Query '{query[:50]}' across all categories: "
            f"returning {min(len(all_results), n_results)} of {len(all_results)} "
            f"(categories: {list(cat_results.keys())}, keywords: {keywords})"
        )
        return all_results[:n_results]

    # ── Collection CRUD ─────────────────────────────────────

    def update_collection_description(self, category: str, name: str, description: str) -> bool:
        """
        Update the description of a collection.

        Args:
            category: Collection category
            name: Collection name
            description: New description text

        Returns:
            True if updated, False if collection not found
        """
        collection_name = _make_collection_name(category, name)

        if not CHROMADB_AVAILABLE or self.client is None:
            if collection_name in self.memory_store:
                self.memory_store[collection_name]["metadata"]["description"] = description
                self.collections[collection_name] = self.memory_store[collection_name]
                self._save_to_disk()
                logger.info(f"Updated description for memory collection: {collection_name}")
                return True
            return False

        try:
            collection = self.client.get_collection(name=collection_name)
            collection.modify(metadata={"description": description})
            logger.info(f"Updated description for collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update description for {collection_name}: {e}")
            return False

    def delete_collection(self, category: str, name: str) -> bool:
        """
        Delete a collection. Refuses to delete system default collections.

        Args:
            category: Collection category
            name: Collection name

        Returns:
            True if deleted, False if protected or not found

        Raises:
            ValueError: if attempting to delete a default collection
        """
        collection_name = _make_collection_name(category, name)

        if _is_default_collection(collection_name):
            raise ValueError(f"默认知识库 '{collection_name}' 不可全库删除，只能删除或编辑其中的单条内容")

        if not CHROMADB_AVAILABLE or self.client is None:
            if collection_name in self.memory_store:
                del self.memory_store[collection_name]
                self.collections.pop(collection_name, None)
                logger.info(f"Deleted memory collection: {collection_name}")
                self._save_to_disk()
                return True
            return False

        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False

    def list_collections(self) -> List[Dict[str, Any]]:
        """
        List all collections with metadata.

        Returns:
            List of dicts: {name, category, display_name, element_count, is_default}
        """
        result = []

        if not CHROMADB_AVAILABLE or self.client is None:
            for cname, cdata in self.memory_store.items():
                parsed = _parse_collection_name(cname)
                if parsed is None:
                    continue
                cat, name = parsed
                meta = cdata.get("metadata", {})
                result.append({
                    "name": cname,
                    "category": cat,
                    "display_name": name,
                    "element_count": len(cdata.get("elements", [])),
                    "is_default": _is_default_collection(cname),
                    "description": meta.get("description", ""),
                })
            return result

        try:
            all_cols = self.client.list_collections()
            for col in all_cols:
                cname = col.name
                parsed = _parse_collection_name(cname)
                if parsed is None:
                    # Legacy or unknown naming; try to read metadata
                    try:
                        meta = col.metadata or {}
                        cat = meta.get("category", "unknown")
                        name = meta.get("name", cname)
                    except Exception:
                        continue
                else:
                    cat, name = parsed
                try:
                    count = col.count()
                except Exception:
                    count = 0
                is_default = _is_default_collection(cname)
                try:
                    ch_meta = col.metadata or {}
                except Exception:
                    ch_meta = {}
                result.append({
                    "name": cname,
                    "category": cat,
                    "display_name": name,
                    "element_count": count,
                    "is_default": is_default,
                    "description": ch_meta.get("description", ""),
                })
            return result
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    def get_collection_count(self, category: str, name: str) -> int:
        """Get number of elements in a collection."""
        collection = self.get_collection(category, name)
        if not collection:
            return 0
        if not CHROMADB_AVAILABLE or self.client is None:
            return len(collection["elements"])
        return collection.count()

    def get_elements(self, category: str, name: str) -> List[Dict[str, Any]]:
        """
        Get all elements in a collection.

        Args:
            category: Collection category
            name: Collection name

        Returns:
            List of element dicts with id, content, metadata
        """
        collection = self.get_collection(category, name)
        if not collection:
            return []

        collection_name = _make_collection_name(category, name)

        if not CHROMADB_AVAILABLE or self.client is None:
            return list(collection["elements"])

        try:
            result = collection.get()
            elements = []
            ids = result.get("ids", [])
            documents = result.get("documents", [])
            metadatas = result.get("metadatas", [])
            for i in range(len(ids)):
                elements.append({
                    "id": ids[i],
                    "content": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                })
            return elements
        except Exception as e:
            logger.error(f"Failed to get elements: {e}")
            return []


# Singleton instance
_chroma_manager: Optional[ChromaManager] = None


def get_chroma_manager(persist_dir: str = ".chroma") -> ChromaManager:
    """Get or create ChromaManager singleton."""
    global _chroma_manager
    if _chroma_manager is None:
        _chroma_manager = ChromaManager(
            persist_dir=persist_dir,
            json_path=".voltaire_knowledge/knowledge_store.json"
        )
    return _chroma_manager
