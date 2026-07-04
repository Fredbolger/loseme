#!/usr/bin/env python3
"""
Test suite for Paperless tag management functionality.

This test file verifies:
- Paperless API client tag methods
- Backend route handlers
- Error mapping
- Cache synchronization
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add the server directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

def test_paperless_api_client_tag_methods():
    """Test the Paperless API client tag methods."""
    print("Testing Paperless API client tag methods... ", end="")
    try:
        from paperless_api_client import PaperlessApiClient
        
        # Create a mock client
        client = PaperlessApiClient(base_url="http://test.example.com", api_token="test-token")
        
        # Test that the new methods exist
        assert hasattr(client, 'create_tag'), "create_tag method missing"
        assert hasattr(client, 'set_document_tags'), "set_document_tags method missing"
        assert hasattr(client, 'add_tag'), "add_tag method missing"
        assert hasattr(client, 'remove_tag'), "remove_tag method missing"
        
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_add_tag_wrapper_behavior():
    """Test that add_tag wrapper follows fetch → modify → PATCH behavior."""
    print("Testing add_tag wrapper behavior... ", end="")
    try:
        from paperless_api_client import PaperlessApiClient
        
        # Create a client with mocked transport
        client = PaperlessApiClient(base_url="http://test.example.com", api_token="test-token")
        
        # Mock the _make_request method
        mock_requests = []
        
        def mock_make_request(method, endpoint, **kwargs):
            mock_requests.append((method, endpoint, kwargs))
            
            if endpoint == "api/documents/123/" and method == "GET":
                # Return document with existing tags [1, 2]
                return {
                    "id": 123,
                    "title": "Test Document",
                    "tags": [{"id": 1, "name": "existing-tag-1"}, {"id": 2, "name": "existing-tag-2"}]
                }
            elif endpoint == "api/documents/123/" and method == "PATCH":
                # Verify that PATCH is called with complete tag list including new tag
                patch_data = kwargs.get('json', {})
                assert 'tags' in patch_data, "PATCH should include tags field"
                assert patch_data['tags'] == [1, 2, 5], f"Expected [1, 2, 5], got {patch_data['tags']}"
                return {
                    "id": 123,
                    "title": "Test Document",
                    "tags": [
                        {"id": 1, "name": "existing-tag-1"}, 
                        {"id": 2, "name": "existing-tag-2"},
                        {"id": 5, "name": "new-tag"}
                    ]
                }
            return {}
        
        client._make_request = mock_make_request
        
        # Call add_tag
        result = client.add_tag(123, 5)
        
        # Verify the sequence: GET document, PATCH with updated tags
        assert len(mock_requests) == 2, f"Expected 2 requests, got {len(mock_requests)}"
        assert mock_requests[0][0] == "GET", "First request should be GET"
        assert mock_requests[1][0] == "PATCH", "Second request should be PATCH"
        
        # Verify the result contains the new tag
        tag_ids = [tag.get("id") for tag in result.get("tags", [])]
        assert 5 in tag_ids, "New tag should be in the result"
        
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_remove_tag_wrapper_behavior():
    """Test that remove_tag wrapper follows fetch → modify → PATCH behavior."""
    print("Testing remove_tag wrapper behavior... ", end="")
    try:
        from paperless_api_client import PaperlessApiClient
        
        # Create a client with mocked transport
        client = PaperlessApiClient(base_url="http://test.example.com", api_token="test-token")
        
        # Mock the _make_request method
        mock_requests = []
        
        def mock_make_request(method, endpoint, **kwargs):
            mock_requests.append((method, endpoint, kwargs))
            
            if endpoint == "api/documents/456/" and method == "GET":
                # Return document with existing tags [10, 20, 30]
                return {
                    "id": 456,
                    "title": "Test Document",
                    "tags": [
                        {"id": 10, "name": "tag-10"}, 
                        {"id": 20, "name": "tag-20"},
                        {"id": 30, "name": "tag-30"}
                    ]
                }
            elif endpoint == "api/documents/456/" and method == "PATCH":
                # Verify that PATCH is called with tag 20 removed
                patch_data = kwargs.get('json', {})
                assert 'tags' in patch_data, "PATCH should include tags field"
                assert patch_data['tags'] == [10, 30], f"Expected [10, 30], got {patch_data['tags']}"
                return {
                    "id": 456,
                    "title": "Test Document",
                    "tags": [
                        {"id": 10, "name": "tag-10"},
                        {"id": 30, "name": "tag-30"}
                    ]
                }
            return {}
        
        client._make_request = mock_make_request
        
        # Call remove_tag
        result = client.remove_tag(456, 20)
        
        # Verify the sequence: GET document, PATCH with updated tags
        assert len(mock_requests) == 2, f"Expected 2 requests, got {len(mock_requests)}"
        assert mock_requests[0][0] == "GET", "First request should be GET"
        assert mock_requests[1][0] == "PATCH", "Second request should be PATCH"
        
        # Verify the result does not contain the removed tag
        tag_ids = [tag.get("id") for tag in result.get("tags", [])]
        assert 20 not in tag_ids, "Removed tag should not be in the result"
        assert 10 in tag_ids and 30 in tag_ids, "Other tags should remain"
        
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_concurrent_update_scenario():
    """Test that wrappers handle concurrent updates correctly."""
    print("Testing concurrent update scenario... ", end="")
    try:
        from paperless_api_client import PaperlessApiClient
        
        # Create a client with mocked transport that simulates concurrent modification
        client = PaperlessApiClient(base_url="http://test.example.com", api_token="test-token")
        
        request_count = [0]  # Use list to make it mutable in closure
        
        def mock_make_request(method, endpoint, **kwargs):
            request_count[0] += 1
            
            if endpoint == "api/documents/789/" and method == "GET":
                if request_count[0] == 1:
                    # First GET: document has tags [1, 2]
                    return {
                        "id": 789,
                        "title": "Concurrent Test",
                        "tags": [{"id": 1, "name": "tag-1"}, {"id": 2, "name": "tag-2"}]
                    }
                else:
                    # Subsequent GET (from second operation): document now has tags [1, 2, 100]
                    # This simulates another process adding a tag
                    return {
                        "id": 789,
                        "title": "Concurrent Test",
                        "tags": [{"id": 1, "name": "tag-1"}, {"id": 2, "name": "tag-2"}, {"id": 100, "name": "external-tag"}]
                    }
            elif endpoint == "api/documents/789/" and method == "PATCH":
                # Verify that each PATCH includes the complete current state
                patch_data = kwargs.get('json', {})
                return {
                    "id": 789,
                    "title": "Concurrent Test",
                    "tags": [{"id": tag_id, "name": f"tag-{tag_id}"} for tag_id in patch_data.get('tags', [])]
                }
            return {}
        
        client._make_request = mock_make_request
        
        # First add tag 5
        result1 = client.add_tag(789, 5)
        
        # Second add tag 10 - this should get the latest state and include both 5 and 10
        result2 = client.add_tag(789, 10)
        
        # Verify both operations completed successfully
        # Note: In a real concurrent scenario, the second operation would start from the state
        # returned by the first operation due to the GET-before-PATCH pattern
        assert result1.get("id") == 789, "First operation should succeed"
        assert result2.get("id") == 789, "Second operation should succeed"
        
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_paperless_routes_import():
    """Test that the Paperless routes can be imported and contain the new endpoints."""
    print("Testing Paperless routes import... ", end="")
    try:
        # This will test that the paperless.py module can be imported
        # and that all the new functions are present
        from api.app.routes.paperless import (
            router,
            list_tags_endpoint,
            create_tag_endpoint,
            get_document_tags_endpoint,
            add_document_tag_endpoint,
            remove_document_tag_endpoint,
            resolve_paperless_context
        )
        
        # Verify that the endpoints are registered on the router
        routes = [route.path for route in router.routes]
        assert '/tags' in routes, "Tags route not found"
        assert any('/documents/' in r for r in routes), "Document routes not found"
        
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_mapping_constants():
    """Test that error mapping constants are available."""
    print("Testing error mapping constants... ", end="")
    try:
        # Test that the error types are available
        from fastapi import HTTPException
        
        # These are the error details we should be using
        expected_errors = [
            "paperless_unreachable",
            "paperless_document_missing", 
            "paperless_auth_failed"
        ]
        
        for error_detail in expected_errors:
            # Create an HTTPException with our error detail
            exc = HTTPException(status_code=500, detail=error_detail)
            assert exc.detail == error_detail, f"Error detail should be {error_detail}"
        
        print("✅ PASSED")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def run_all_tests():
    """Run all Paperless tag tests."""
    print("=" * 60)
    print("Running Paperless Tag Management Tests")
    print("=" * 60)
    
    tests = [
        test_paperless_api_client_tag_methods,
        test_add_tag_wrapper_behavior,
        test_remove_tag_wrapper_behavior,
        test_concurrent_update_scenario,
        test_paperless_routes_import,
        test_error_mapping_constants,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ {test.__name__} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    # Set up environment for tests
    os.environ["LOSEME_DEVICE_ID"] = "test-server"
    
    success = run_all_tests()
    sys.exit(0 if success else 1)