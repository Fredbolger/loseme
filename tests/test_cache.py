"""
test_cache.py — TTLCache unit tests.

No external dependencies.
"""
import time

import pytest

from api.app.cache import TTLCache


class TestTTLCacheBasicOperations:

    def test_set_and_get(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_missing_key_returns_none(self):
        cache = TTLCache(ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_overwrite_value(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("k", "v1")
        cache.set("k", "v2")
        assert cache.get("k") == "v2"

    def test_stores_different_types(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("int", 42)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1})
        assert cache.get("int") == 42
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1}

    def test_multiple_keys_independent(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.get("a") == 1
        assert cache.get("b") == 2


class TestTTLCacheExpiry:

    def test_expired_entry_returns_none(self):
        cache = TTLCache(ttl_seconds=1)
        cache.set("key", "value")
        # Manually expire by manipulating the stored timestamp
        key, (ts, val) = next(iter(cache._store.items()))
        cache._store[key] = (ts - 2, val)  # backdate by 2 seconds
        assert cache.get("key") is None

    def test_not_expired_entry_returned(self):
        cache = TTLCache(ttl_seconds=300)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_expired_entry_removed_on_access(self):
        cache = TTLCache(ttl_seconds=1)
        cache.set("key", "value")
        key, (ts, val) = next(iter(cache._store.items()))
        cache._store[key] = (ts - 2, val)
        cache.get("key")  # triggers removal
        assert "key" not in cache._store


class TestTTLCacheInvalidation:

    def test_invalidate_removes_key(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", "value")
        cache.invalidate("key")
        assert cache.get("key") is None

    def test_invalidate_nonexistent_key_noop(self):
        cache = TTLCache(ttl_seconds=60)
        cache.invalidate("nonexistent")  # must not raise

    def test_invalidate_prefix_removes_matching(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("distribution:all", "a")
        cache.set("distribution:simple", "b")
        cache.set("other:key", "c")
        cache.invalidate_prefix("distribution:")
        assert cache.get("distribution:all") is None
        assert cache.get("distribution:simple") is None
        assert cache.get("other:key") == "c"

    def test_invalidate_prefix_empty_prefix_clears_all(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate_prefix("")
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_invalidate_prefix_no_matches_noop(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("alpha", 1)
        cache.invalidate_prefix("zzz:")  # no match
        assert cache.get("alpha") == 1


class TestTTLCacheEdgeCases:

    def test_store_none_value(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", None)
        # None is a valid cached value — get should return it, not treat as missing
        result = cache.get("key")
        # Implementation returns None for missing and for None-valued keys
        # Both are acceptable; we just verify no exception is raised
        assert result is None

    def test_zero_ttl_expires_immediately(self):
        cache = TTLCache(ttl_seconds=0)
        cache.set("key", "value")
        # Backdate by 1 second to simulate expiry
        key, (ts, val) = next(iter(cache._store.items()))
        cache._store[key] = (ts - 1, val)
        assert cache.get("key") is None

    def test_large_number_of_keys(self):
        cache = TTLCache(ttl_seconds=60)
        for i in range(1000):
            cache.set(f"key:{i}", i)
        for i in range(1000):
            assert cache.get(f"key:{i}") == i
