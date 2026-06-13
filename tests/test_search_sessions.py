"""
Search session tests.

Covers:
- Session creation and persistence
- Semantic cache hits and misses
- Background refresh is triggered on cache hit
- Chat follow-up stores messages and runs sub-search
- Session delete
- API contract (field shapes, status codes)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from storage.metadata_db.search_sessions import (
    add_message,
    create_session,
    find_similar_session,
    get_session,
    init_search_history_schema,
    list_sessions,
)
from tests.helpers import client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DIM = 4  # tiny embedding dimension for tests


@pytest.fixture(autouse=True)
def _schema(setup_db):
    """Ensure search history tables exist in the temp DB."""
    init_search_history_schema()


@pytest.fixture()
def dummy_embedder():
    """Returns a fixed embedding for every input."""
    embedder = MagicMock()
    embedder.embed.return_value = [1.0, 0.0, 0.0, 0.0]
    return embedder


@pytest.fixture(autouse=True)
def _patch_deps(dummy_embedder):
    """Patch the vector store and LLM so tests stay offline."""
    store = MagicMock()
    store.search.return_value = [
        {"document_part_id": "part-1", "chunk_id": "chunk-1", "score": 0.9, "metadata": {}}
    ]

    with (
        patch("api.app.routes.search.get_embedding_provider", return_value=dummy_embedder),
        patch("api.app.routes.search.get_vector_store", return_value=store),
        patch("api.app.routes.search.stream_llm_answer", new=AsyncMock(return_value="Test answer.")),
        patch("api.app.routes.search.build_chat_context", return_value=[]),
    ):
        yield store


# ---------------------------------------------------------------------------
# Storage layer
# ---------------------------------------------------------------------------

class TestSearchSessionStorage:

    def test_create_and_retrieve(self):
        session = create_session("s1", "test query", [0.1, 0.2], ["part-1"])
        loaded = get_session("s1")
        assert loaded is not None
        assert loaded.query == "test query"
        assert loaded.result_ids == ["part-1"]

    def test_messages_attached_to_session(self):
        create_session("s2", "query", [0.1, 0.2], [])
        add_message("m1", "s2", "user", "hello")
        add_message("m2", "s2", "assistant", "world")
        session = get_session("s2")
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"

    def test_list_sessions_newest_first(self):
        create_session("old", "old query", [0.0, 1.0], [])
        create_session("new", "new query", [1.0, 0.0], [])
        # Touch "new" to push its updated_at forward
        add_message("mx", "new", "user", "ping")
        sessions = list_sessions()
        assert sessions[0].id == "new"

    def test_find_similar_above_threshold(self):
        create_session("cache1", "machine learning", [1.0, 0.0, 0.0, 0.0], ["part-x"])
        result = find_similar_session([1.0, 0.0, 0.0, 0.0], threshold=0.99)
        assert result is not None
        session, score = result
        assert session.id == "cache1"
        assert score == pytest.approx(1.0)

    def test_find_similar_below_threshold_returns_none(self):
        create_session("cache2", "python programming", [1.0, 0.0, 0.0, 0.0], [])
        result = find_similar_session([0.0, 1.0, 0.0, 0.0], threshold=0.99)
        assert result is None

    def test_empty_store_returns_none(self):
        assert find_similar_session([1.0, 0.0, 0.0, 0.0]) is None


# ---------------------------------------------------------------------------
# POST /search — cache miss
# ---------------------------------------------------------------------------

class TestSearchCacheMiss:

    def test_returns_200(self):
        resp = client.post("/search", json={"query": "hello", "top_k": 3})
        assert resp.status_code == 200

    def test_returns_session_id(self):
        resp = client.post("/search", json={"query": "hello", "top_k": 3})
        assert "session_id" in resp.json()
        assert resp.json()["session_id"]

    def test_cache_hit_is_false(self):
        resp = client.post("/search", json={"query": "hello", "top_k": 3})
        assert resp.json()["cache_hit"] is False

    def test_answer_is_present(self):
        resp = client.post("/search", json={"query": "hello", "top_k": 3})
        assert resp.json()["answer"] == "Test answer."

    def test_session_persisted(self):
        resp = client.post("/search", json={"query": "persisted query", "top_k": 3})
        session_id = resp.json()["session_id"]
        session = get_session(session_id)
        assert session is not None
        assert session.query == "persisted query"

    def test_messages_stored(self):
        resp = client.post("/search", json={"query": "stored messages", "top_k": 3})
        session = get_session(resp.json()["session_id"])
        roles = [m.role for m in session.messages]
        assert "user" in roles
        assert "assistant" in roles


# ---------------------------------------------------------------------------
# POST /search — cache hit
# ---------------------------------------------------------------------------

class TestSearchCacheHit:

    def test_cache_hit_flag_set(self):
        # First search seeds the cache
        client.post("/search", json={"query": "neural networks", "top_k": 3})
        # Identical query → should hit the cache
        resp = client.post("/search", json={"query": "neural networks", "top_k": 3})
        assert resp.json()["cache_hit"] is True

    def test_cache_score_present_on_hit(self):
        client.post("/search", json={"query": "vector search", "top_k": 3})
        resp = client.post("/search", json={"query": "vector search", "top_k": 3})
        assert resp.json()["cache_score"] is not None

    def test_cache_miss_with_low_threshold(self):
        """Setting threshold=1.1 forces a cache miss even for identical queries."""
        client.post("/search", json={"query": "cache miss forced", "top_k": 3})
        resp = client.post(
            "/search",
            json={"query": "cache miss forced", "top_k": 3, "cache_threshold": 1.1},
        )
        assert resp.json()["cache_hit"] is False


# ---------------------------------------------------------------------------
# GET /search/history
# ---------------------------------------------------------------------------

class TestSearchHistory:

    def test_returns_200(self):
        assert client.get("/search/history").status_code == 200

    def test_has_sessions_key(self):
        assert "sessions" in client.get("/search/history").json()

    def test_session_appears_after_search(self):
        client.post("/search", json={"query": "history test", "top_k": 3})
        sessions = client.get("/search/history").json()["sessions"]
        queries = [s["query"] for s in sessions]
        assert "history test" in queries

    def test_session_has_required_fields(self):
        client.post("/search", json={"query": "field check", "top_k": 3})
        sessions = client.get("/search/history").json()["sessions"]
        required = {"session_id", "query", "result_count", "updated_at"}
        for s in sessions:
            assert required.issubset(s.keys())


# ---------------------------------------------------------------------------
# GET /search/sessions/{id}
# ---------------------------------------------------------------------------

class TestSessionDetail:

    def test_returns_404_for_unknown(self):
        assert client.get("/search/sessions/nonexistent").status_code == 404

    def test_returns_full_messages(self):
        resp = client.post("/search", json={"query": "detail test", "top_k": 3})
        sid = resp.json()["session_id"]
        detail = client.get(f"/search/sessions/{sid}").json()
        assert "messages" in detail
        assert len(detail["messages"]) >= 2  # user + assistant


# ---------------------------------------------------------------------------
# POST /search/sessions/{id}/chat
# ---------------------------------------------------------------------------

class TestChatFollowUp:

    def test_follow_up_returns_200(self):
        resp = client.post("/search", json={"query": "base query", "top_k": 3})
        sid = resp.json()["session_id"]
        follow = client.post(
            f"/search/sessions/{sid}/chat",
            json={"message": "tell me more", "top_k": 2},
        )
        assert follow.status_code == 200

    def test_follow_up_answer_present(self):
        resp = client.post("/search", json={"query": "follow up base", "top_k": 3})
        sid = resp.json()["session_id"]
        follow = client.post(
            f"/search/sessions/{sid}/chat",
            json={"message": "elaborate please", "top_k": 2},
        )
        assert follow.json()["answer"] == "Test answer."

    def test_follow_up_messages_persisted(self):
        resp = client.post("/search", json={"query": "persist follow", "top_k": 3})
        sid = resp.json()["session_id"]
        client.post(
            f"/search/sessions/{sid}/chat",
            json={"message": "follow up", "top_k": 2},
        )
        detail = client.get(f"/search/sessions/{sid}").json()
        roles = [m["role"] for m in detail["messages"]]
        assert roles.count("user") == 2
        assert roles.count("assistant") == 2

    def test_chat_on_nonexistent_session_returns_404(self):
        resp = client.post(
            "/search/sessions/ghost/chat",
            json={"message": "hello", "top_k": 2},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /search/sessions/{id}
# ---------------------------------------------------------------------------

class TestSessionDelete:

    def test_delete_returns_200(self):
        resp = client.post("/search", json={"query": "to delete", "top_k": 3})
        sid = resp.json()["session_id"]
        assert client.delete(f"/search/sessions/{sid}").status_code == 200

    def test_deleted_session_not_retrievable(self):
        resp = client.post("/search", json={"query": "gone", "top_k": 3})
        sid = resp.json()["session_id"]
        client.delete(f"/search/sessions/{sid}")
        assert client.get(f"/search/sessions/{sid}").status_code == 404

    def test_delete_nonexistent_returns_404(self):
        assert client.delete("/search/sessions/phantom").status_code == 404
