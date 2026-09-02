"""
Weaviate 适配器单元测试。
"""

from __future__ import annotations

from unittest.mock import MagicMock


def test_weaviate_delete_uses_native_id():
    from memory_manager.vector_db.weaviate_adapter import WeaviateVectorDB

    db = WeaviateVectorDB(url="http://localhost:8080")
    mock_client = MagicMock()
    db._client = mock_client
    db._is_connected = True

    result = db.delete("memory_collection", 'id == "abc-123"')

    mock_client.data_object.delete.assert_called_once_with(
        uuid="abc-123",
        class_name="Memory_collection",
    )
    assert result.delete_count == 1


def test_weaviate_query_returns_additional_id():
    from memory_manager.vector_db.weaviate_adapter import WeaviateVectorDB

    db = WeaviateVectorDB(url="http://localhost:8080")
    mock_query = MagicMock()
    mock_query.with_additional.return_value = mock_query
    mock_query.with_limit.return_value = mock_query
    mock_query.do.return_value = {
        "data": {
            "Get": {
                "Memory_collection": [
                    {
                        "content": "hello",
                        "session_id": "s1",
                        "_additional": {"id": "abc-123"},
                    }
                ]
            }
        }
    }

    mock_client = MagicMock()
    mock_client.query.get.return_value = mock_query
    db._client = mock_client
    db._is_connected = True

    records = db.query("memory_collection", None, ["content", "session_id"], limit=1)

    mock_query.with_additional.assert_called_once_with(["id"])
    assert records[0]["id"] == "abc-123"
    assert records[0]["content"] == "hello"
