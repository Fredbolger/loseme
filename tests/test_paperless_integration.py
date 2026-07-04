#!/usr/bin/env python3
"""
Test suite for Paperless-ngx integration.

This test file verifies that all the implemented Paperless functionality
works correctly without causing errors.
"""

import sys
import sqlite3
import tempfile
import os
import json

def test_core_models_imports():
    """Test that all core model imports work."""
    print("Testing Core Models Imports... ", end="")
    try:
        from loseme_core.paperless_model import PaperlessIndexingScope, PaperlessDocument, PaperlessIngestRequest
        from loseme_core.models import IngestRequest
        from loseme_core.ids import make_paperless_source_id
        from loseme_core.scope_models import IndexingScope
        from loseme_core.document_models import Document
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_core_models_functionality():
    """Test core model functionality."""
    print("Testing Core Models Functionality... ", end="")
    try:
        from loseme_core.paperless_model import PaperlessIndexingScope
        from loseme_core.scope_models import IndexingScope
        
        # Test creation
        scope = PaperlessIndexingScope(
            connection_id='test-conn-123',
            tag_ids=[1, 2, 3],
            correspondent_ids=[4],
            document_type_ids=[5]
        )
        assert scope.type == "paperless"
        assert scope.connection_id == "test-conn-123"
        assert scope.tag_ids == [1, 2, 3]
        
        # Test serialization
        serialized = scope.serialize()
        assert "type" in serialized
        assert serialized["type"] == "paperless"
        assert serialized["connection_id"] == "test-conn-123"
        
        # Test deserialization
        deserialized = IndexingScope.deserialize(serialized)
        assert deserialized.connection_id == "test-conn-123"
        assert deserialized.tag_ids == [1, 2, 3]
        
        # Test locator
        locator = scope.locator()
        assert locator.startswith("paperless:")
        assert "test-conn-123" in locator
        
        # Test hash
        hash_val = scope.hash()
        assert len(hash_val) == 64  # SHA256 hex digest
        
        # Test Document source_type validation
        from loseme_core.document_models import Document
        from pydantic import ValidationError
        
        # Valid paperless document
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
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_database_imports():
    """Test that database imports work."""
    print("Testing Database Imports... ", end="")
    try:
        from storage.metadata_db.paperless_connections import (
            create_paperless_connection, get_paperless_connection, 
            list_paperless_connections, update_paperless_connection, 
            delete_paperless_connection, validate_paperless_connection,
            PaperlessConnection
        )
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_database_schema():
    """Test that the database schema works."""
    print("Testing Database Schema... ", end="")
    try:
        # Create temp database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        conn = None
        try:
            conn = sqlite3.connect(db_path)
            conn.execute('PRAGMA foreign_keys = ON')

            # Run the migration
            from storage.metadata_db.db import init_db
            init_db()
            
            # Check paperless_connections table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='paperless_connections'"
            )
            result = cursor.fetchone()
            assert result is not None, "paperless_connections table not found"
            assert result[0] == "paperless_connections"

            # Check table structure
            cursor = conn.execute("PRAGMA table_info(paperless_connections)")
            columns = [col[1] for col in cursor.fetchall()]  # column names
            required_columns = ['id', 'base_url', 'api_token', 'created_at', 'updated_at']
            for col in required_columns:
                assert col in columns, f"Missing column: {col}"

            print("✅ PASSED")
            return True
        finally:
            if conn:
                conn.close()
            os.unlink(db_path)
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_database_crud():
    """Test CRUD operations on paperless_connections."""
    print("Testing Database CRUD Operations... ", end="")
    try:
        from storage.metadata_db.paperless_connections import (
            create_paperless_connection, get_paperless_connection, 
            list_paperless_connections, update_paperless_connection, 
            delete_paperless_connection
        )
        from storage.metadata_db.db import get_connection
        
        # Use temp database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        # Override DB_PATH for testing
        import storage.metadata_db.db
        original_db_path = storage.metadata_db.db.DB_PATH
        storage.metadata_db.db.DB_PATH = sqlite3.connect(db_path)

        try:
            # Initialize database
            from storage.metadata_db.db import init_db
            init_db()
            
            # Create connection
            conn = create_paperless_connection("http://test.example.com", "test-token-123")
            assert conn.id is not None
            assert conn.base_url == "http://test.example.com"
            assert conn.api_token == "test-token-123"
            conn_id = conn.id
            
            # Get connection
            fetched_conn = get_paperless_connection(conn_id)
            assert fetched_conn is not None
            assert fetched_conn.base_url == "http://test.example.com"
            
            # List connections
            connections = list_paperless_connections()
            assert len(connections) == 1
            assert connections[0].id == conn_id
            
            # Update connection
            updated_conn = update_paperless_connection(conn_id, base_url="http://updated.example.com")
            assert updated_conn is not None
            assert updated_conn.base_url == "http://updated.example.com"
            
            # Delete connection
            deleted = delete_paperless_connection(conn_id)
            assert deleted is True
            
            # Verify deletion
            final_conn = get_paperless_connection(conn_id)
            assert final_conn is None

            print("✅ PASSED")
            return True
        finally:
            storage.metadata_db.db.DB_PATH = original_db_path
            os.unlink(db_path)
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_api_client_import():
    """Test that API client imports work."""
    print("Testing API Client Import... ", end="")
    try:
        from paperless_api_client import PaperlessApiClient
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_ingestion_source_import():
    """Test that ingestion source imports work."""
    print("Testing Ingestion Source Import... ", end="")
    try:
        from paperless_ingestion import PaperlessIngestionSource
        from ingestion_sources import create_ingestion_source_from_scope, get_ingestion_source
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_preview_generator_import():
    """Test that preview generator imports work."""
    print("Testing Preview Generator Import... ", end="")
    try:
        from preview.generators.paperless import PaperlessDocumentPreviewGenerator
        from preview.registry import preview_registry
        
        # Check that it's registered
        generators = preview_registry.list_generators()
        assert "paperless_document" in generators
        
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_server_routes_import():
    """Test that server routes import correctly."""
    print("Testing Server Routes Import... ", end="")
    try:
        from api.app.routes.paperless import router as paperless_router
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_server_app_integration():
    """Test that the server app integrates paperless routes."""
    print("Testing Server App Integration... ", end="")
    try:
        from api.app.main import app
        routes = [route.path for route in app.routes]
        paperless_routes = [r for r in routes if '/paperless' in r]
        assert len(paperless_routes) > 0, "No paperless routes found"
        print(f"✅ PASSED ({len(paperless_routes)} paperless routes registered)")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def run_all_tests():
    """Run all Paperless integration tests."""
    print("=" * 60)
    print("PAPERLESS-NGX INTEGRATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_core_models_imports,
        test_core_models_functionality,
        test_database_imports,
        test_database_schema,
        test_database_crud,
        test_api_client_import,
        test_ingestion_source_import,
        test_preview_generator_import,
        test_server_routes_import,
        test_server_app_integration,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ FAILED with exception: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"⚠️  {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())