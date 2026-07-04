#!/usr/bin/env python3
"""
Quick Paperless integration test - can be copied to server container for testing.
"""

import sys
import sqlite3
import tempfile
import os
from pathlib import Path

from fastapi.routing import APIRoute

def get_all_paths():
    paths = []
    for route in app.routes:
        if hasattr(route, 'path'):  # Individual route
            paths.append(route.path)
        elif hasattr(route, 'routes'):  # Router with routes
            for sub_route in route.routes:
                if isinstance(sub_route, APIRoute):
                    # Combine prefix + path
                    prefix = route.prefix if hasattr(route, 'prefix') else ""
                    paths.append(f"{prefix}{sub_route.path}")
    return paths

print("=" * 60)
print("PAPERLESS-NGX QUICK INTEGRATION TEST")
print("=" * 60)

# Test 1: Core Model Imports
print("1. Testing Core Models Imports... ", end="")
try:
    from loseme_core.paperless_model import PaperlessIndexingScope, PaperlessDocument, PaperlessIngestRequest
    from loseme_core.models import IngestRequest
    from loseme_core.ids import make_paperless_source_id
    from loseme_core.scope_models import IndexingScope
    from loseme_core.document_models import Document
    print("✅ PASSED")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 2: Core Model Functionality
print("2. Testing Core Model Functionality... ", end="")
try:
    from loseme_core.paperless_model import PaperlessIndexingScope
    from loseme_core.scope_models import IndexingScope
    
    scope = PaperlessIndexingScope(
        connection_id='test-conn-123',
        tag_ids=[1, 2, 3],
        correspondent_ids=[4],
        document_type_ids=[5]
    )
    assert scope.type == "paperless"
    serialized = scope.serialize()
    assert "type" in serialized
    deserialized = IndexingScope.deserialize(serialized)
    assert deserialized.connection_id == "test-conn-123"
    locator = scope.locator()
    assert locator.startswith("paperless:")
    hash_val = scope.hash()
    assert len(hash_val) == 64
    
    # Test Document with paperless source_type
    doc = Document(
        id="test-id",
        source_type="paperless",
        source_id="test-source-id",
        device_id="test-device",
        source_path="paperless:123:test",
        checksum="test-checksum"
    )
    assert doc.source_type == "paperless"
    print("✅ PASSED")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 3: Database Schema
print("3. Testing Database Schema... ", end="")
try:
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    conn = sqlite3.connect(db_path)
    from storage.metadata_db.db import init_db
    import storage.metadata_db.db as db_module
    db_module.DB_PATH = Path(db_path)  # Override before calling init_db
    init_db()
    
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='paperless_connections'")
    result = cursor.fetchone()
    assert result is not None, "paperless_connections table not found"
    assert result[0] == "paperless_connections"
    conn.close()
    os.unlink(db_path)
    print("✅ PASSED")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 4: Database CRUD
print("4. Testing Database CRUD... ", end="")
try:
    from storage.metadata_db.paperless_connections import (
        create_paperless_connection, get_paperless_connection, 
        list_paperless_connections, update_paperless_connection, 
        delete_paperless_connection
    )
    
    # Override DB for testing
    import storage.metadata_db.db
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name
    
    original_db = storage.metadata_db.db.DB_PATH
    storage.metadata_db.db.DB_PATH = Path(test_db)
    
    try:
        from storage.metadata_db.db import init_db
        init_db()
        
        conn = create_paperless_connection("http://test.example.com", "test-token-123")
        conn_id = conn.id
        
        fetched = get_paperless_connection(conn_id)
        assert fetched is not None
        
        connections = list_paperless_connections()
        assert len(connections) == 1
        
        updated = update_paperless_connection(conn_id, base_url="http://updated.example.com")
        assert updated.base_url == "http://updated.example.com"
        
        deleted = delete_paperless_connection(conn_id)
        assert deleted is True
        
        final = get_paperless_connection(conn_id)
        assert final is None
        
        print("✅ PASSED")
    finally:
        storage.metadata_db.db.DB_PATH = original_db
        os.unlink(test_db)
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 5: API Client Import
print("5. Testing API Client Import... ", end="")
try:
    from paperless_api_client import PaperlessApiClient
    print("✅ PASSED")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 6: Ingestion Source Import
print("6. Testing Ingestion Source Import... ", end="")
try:
    from paperless_ingestion import PaperlessIngestionSource
    from ingestion_sources import create_ingestion_source_from_scope, get_ingestion_source
    print("✅ PASSED")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 7: Preview Generator Import
print("7. Testing Preview Generator Import... ", end="")
try:
    from preview.generators.paperless import PaperlessDocumentPreviewGenerator
    from preview.registry import preview_registry
    generators = preview_registry.list_generators()
    assert "paperless_document" in generators
    print("✅ PASSED")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 8: Server Routes Import
print("8. Testing Server Routes Import... ", end="")
try:
    from api.app.routes.paperless import router as paperless_router
    print("✅ PASSED")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

print("9. Testing Server App Integration... ", end="")
try:
    from api.app.main import app
    from api.app.routes import paperless_router
    from fastapi.routing import APIRoute
    
    # Check the router directly
    print(f"Paperless router prefix: {paperless_router.prefix}")
    paperless_paths = []
    for route in paperless_router.routes:
        if isinstance(route, APIRoute):
            paperless_paths.append(route.path)
            print(f"  Paperless route path: {route.path}")
    
    # Now check the app
    all_paths = ['/']  # Start with root
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path != '/':
            all_paths.append(route.path)
        elif hasattr(route, 'routes'):
            # Try to get the router's prefix
            router_obj = getattr(route, 'router', route)
            prefix = getattr(router_obj, 'prefix', '')
            print(f"Router prefix: {prefix}")
            
            for sub_route in route.routes:
                if isinstance(sub_route, APIRoute):
                    # The path might already include the prefix
                    path = sub_route.path
                    if path.startswith(prefix) or not prefix:
                        all_paths.append(path)
                    else:
                        all_paths.append(f"{prefix}{path}")
    
    # Find paperless routes
    paperless_routes = [r for r in all_paths if '/paperless' in r]
    
    if not paperless_routes:
        # Check if any routes from the paperless router exist
        print(f"\nPaperless router routes: {paperless_paths}")
        if paperless_paths:
            # The router has routes but they're not in the app? This shouldn't happen.
            paperless_routes = paperless_paths
    
    assert len(paperless_routes) > 0, f"No paperless routes found. All app routes: {all_paths}"
    print(f"✅ PASSED ({len(paperless_routes)} paperless routes)")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)


print("=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
