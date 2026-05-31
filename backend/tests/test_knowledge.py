"""Tests for knowledge management system"""

import pytest
import tempfile
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from knowledge.chroma_manager import ChromaManager, CHROMADB_AVAILABLE, SYSTEM_DEFAULT_NAMES
from knowledge.llama_processor import LlamaProcessor


def test_chroma_manager_init():
    """Test ChromaManager initialization"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ChromaManager(persist_dir=tmpdir, json_path=os.path.join(tmpdir, "store.json"))
        if CHROMADB_AVAILABLE:
            assert manager.client is not None
        else:
            assert manager.memory_store is not None
            assert manager.collections is not None
        # Default collections should be auto-created
        cols = manager.list_collections()
        assert len(cols) >= 3  # 3 default collections
        default_names = [c["name"] for c in cols]
        for dn in SYSTEM_DEFAULT_NAMES:
            assert dn in default_names


def test_chroma_manager_create_collection():
    """Test creating a collection"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ChromaManager(persist_dir=tmpdir, json_path=os.path.join(tmpdir, "store.json"))

        collection = manager.create_collection("table", "test_site")
        assert collection is not None
        full_name = "table_test_site"
        names = [c["name"] for c in manager.list_collections()]
        assert full_name in names
        assert manager.get_collection_count("table", "test_site") == 0


def test_chroma_manager_add_elements():
    """Test adding elements to collection"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ChromaManager(persist_dir=tmpdir, json_path=os.path.join(tmpdir, "store.json"))

        elements = [
            {
                "id": "btn1",
                "content": "Login button with text 'Login'",
                "metadata": {
                    "type": "button",
                    "selector": "#login-btn",
                    "actions": ["click"]
                }
            },
            {
                "id": "input1",
                "content": "Username input field",
                "metadata": {
                    "type": "input",
                    "selector": "#username",
                    "actions": ["fill"]
                }
            }
        ]

        manager.add_elements("table", "test_site", elements)

        assert manager.get_collection_count("table", "test_site") == 2


def test_chroma_manager_query_elements():
    """Test querying elements by semantic search"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ChromaManager(persist_dir=tmpdir, json_path=os.path.join(tmpdir, "store.json"))

        elements = [
            {
                "id": "btn_login",
                "content": "Login button - click to submit form",
                "metadata": {"type": "button", "selector": "#login"}
            },
            {
                "id": "btn_submit",
                "content": "Submit button for registration",
                "metadata": {"type": "button", "selector": "#submit"}
            },
            {
                "id": "input_email",
                "content": "Email input field for login",
                "metadata": {"type": "input", "selector": "#email"}
            }
        ]

        manager.add_elements("table", "test_site", elements)

        # Query for login related elements
        results = manager.query_elements("table", "test_site", "login button", n_results=2)

        assert len(results) <= 2
        if len(results) > 0:
            assert all(elem['id'] for elem in results)
            assert all(elem['content'] for elem in results)


def test_chroma_manager_delete_collection():
    """Test deleting a collection (non-default)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ChromaManager(persist_dir=tmpdir, json_path=os.path.join(tmpdir, "store.json"))

        manager.create_collection("table", "test_delete")
        full_name = "table_test_delete"
        names = [c["name"] for c in manager.list_collections()]
        assert full_name in names

        manager.delete_collection("table", "test_delete")
        names = [c["name"] for c in manager.list_collections()]
        assert full_name not in names


def test_chroma_manager_default_protection():
    """Test that default collections cannot be deleted"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ChromaManager(persist_dir=tmpdir, json_path=os.path.join(tmpdir, "store.json"))

        with pytest.raises(ValueError, match="默认知识库"):
            manager.delete_collection("table", "default")


def test_chroma_manager_element_crud():
    """Test single element delete and update"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ChromaManager(persist_dir=tmpdir, json_path=os.path.join(tmpdir, "store.json"))

        elements = [{"id": "e1", "content": "Test content", "metadata": {"key": "val"}}]
        manager.add_elements("table", "default", elements)
        assert manager.get_collection_count("table", "default") >= 1

        # Update
        manager.update_element("table_default", "e1", content="New content")
        all_elems = manager.get_elements("table", "default")
        updated = [e for e in all_elems if e["id"] == "e1"]
        assert len(updated) == 1
        assert updated[0]["content"] == "New content"

        # Delete
        manager.delete_element("table_default", "e1")
        all_elems = manager.get_elements("table", "default")
        assert not any(e["id"] == "e1" for e in all_elems)


def test_llama_processor_process_dom_elements():
    """Test processing DOM elements into documents"""
    processor = LlamaProcessor()

    elements = [
        {
            "type": "button",
            "selector": "#login-btn",
            "text": "Login",
            "actions": ["click"],
            "position": {"x": 100, "y": 200}
        },
        {
            "type": "input",
            "selector": "#username",
            "text": "",
            "actions": ["fill"],
            "position": {"x": 50, "y": 150}
        }
    ]

    documents = processor.process_dom_elements(elements)

    assert len(documents) == 2
    assert all(doc.text for doc in documents)
    assert all(doc.metadata for doc in documents)

    login_doc = documents[0]
    assert login_doc.metadata["element_type"] == "button"
    assert login_doc.metadata["selector"] == "#login-btn"
    assert "Login" in login_doc.text


def test_llama_processor_create_description():
    """Test creating element descriptions"""
    processor = LlamaProcessor()

    element = {
        "type": "button",
        "selector": "#submit-btn",
        "text": "Submit",
        "actions": ["click"],
        "position": {"x": 300, "y": 400}
    }

    description = processor._create_element_description(element)

    assert "button" in description
    assert "Submit" in description
    assert "#submit-btn" in description
    assert "click" in description


def test_llama_processor_with_chroma():
    """Test end-to-end processing and storage"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ChromaManager(persist_dir=tmpdir, json_path=os.path.join(tmpdir, "store.json"))
        processor = LlamaProcessor()

        elements = [
            {
                "type": "button",
                "selector": "#search-btn",
                "text": "Search",
                "actions": ["click"],
                "position": {"x": 100, "y": 200}
            }
        ]

        # Process and store with new API
        processor.process_and_store(
            elements,
            category="sitemap",
            name="test_site",
            chroma_manager=manager
        )

        assert manager.get_collection_count("sitemap", "test_site") == 1

        results = manager.query_elements("sitemap", "test_site", "search", n_results=1)
        if CHROMADB_AVAILABLE and len(results) > 0:
            assert "search" in results[0]['content'].lower()