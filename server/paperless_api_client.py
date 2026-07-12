"""
Paperless-ngx API client for Loseme integration.

This module provides a reusable API wrapper for interacting with Paperless-ngx instances.
It supports pagination, filtering, and all the methods required for document ingestion.

The client handles authentication with API tokens and provides a clean interface
for the Loseme system to interact with Paperless-ngx.
"""

import requests
import json
from typing import Optional, List, Dict, Any, Generator, Tuple
from datetime import datetime
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class PaperlessApiClient:
    """
    Client for interacting with the Paperless-ngx REST API.
    
    Paperless-ngx API Documentation: https://paperless-ngx.readthedocs.io/en/latest/api.html
    """
    
    def __init__(self, base_url: str, api_token: str, timeout: int = 30):
        """
        Initialize the Paperless API client.
        
        Args:
            base_url: Base URL of the Paperless-ngx instance (e.g., "http://localhost:8000")
            api_token: API token for authentication
            timeout: Request timeout in seconds (default: 30)
        """
        # Clean up the base URL
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout
        
        # Set up session with authentication
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        # Configure session to preserve Authorization header on same-host redirects
        # This is needed for Paperless-ngx when it redirects HTTP to HTTPS
        self.session.trust_env = False  # Don't use environment variables for proxy settings
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make a request to the Paperless API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (relative to base URL)
            **kwargs: Additional arguments passed to requests Session method
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.exceptions.RequestException: If the request fails
            ValueError: If the response is not valid JSON or has an error status
        """
        url = urljoin(f"{self.base_url}/", endpoint)
        
        try:
            response = getattr(self.session, method.lower())(url, timeout=self.timeout, **kwargs)
            
            # Check for error status codes
            if response.status_code >= 400:
                error_msg = f"Paperless API error {response.status_code}: {response.text}"
                if response.status_code == 401:
                    error_msg = "Paperless API authentication failed: Invalid token or unauthorized"
                elif response.status_code == 404:
                    error_msg = f"Paperless API endpoint not found: {endpoint}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                # If not JSON, return text content for non-JSON endpoints (like document content)
                if response.status_code == 200:
                    return {"content": response.text, "content_type": response.headers.get("Content-Type")}
                else:
                    raise ValueError(f"Invalid JSON response: {response.text}")
                    
        except requests.exceptions.Timeout:
            logger.error(f"Paperless API request timeout for endpoint: {endpoint}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Paperless API request failed for endpoint {endpoint}: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test that the connection to Paperless is working.
        
        Returns:
            True if the connection is successful, False otherwise
        """
        try:
            # Use a simple endpoint that doesn't require authentication to test basic connectivity
            # Then test with an authenticated endpoint
            response = self._make_request("GET", "api/tags/", params={"page_size": 1})
            return True
        except Exception as e:
            logger.warning(f"Paperless connection test failed: {str(e)}")
            return False
    
    def list_tags(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        List all document tags.
        
        Args:
            page: Page number (default: 1)
            page_size: Number of results per page (default: 100)
            
        Returns:
            Dictionary with tags and pagination info
        """
        params = {"page": page, "page_size": page_size}
        return self._make_request("GET", "api/tags/", params=params)
    
    def list_all_tags(self) -> List[Dict[str, Any]]:
        """
        Get all tags, handling pagination automatically.
        
        Returns:
            List of all tag objects
        """
        all_tags = []
        page = 1
        
        while True:
            response = self.list_tags(page=page, page_size=100)
            results = response.get("results", [])
            all_tags.extend(results)
            
            # Check if there are more pages
            if not response.get("next"):
                break
            
            page += 1
            if page > 50:  # Safety limit to prevent infinite loops
                logger.warning("Reached maximum page count (50) while fetching tags")
                break
        
        return all_tags
    
    def create_tag(self, name: str, color: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new tag.
        
        Args:
            name: The name of the tag
            color: Optional color for the tag (hex color code)
            
        Returns:
            The created tag object
        """
        payload = {"name": name}
        if color:
            payload["color"] = color
            
        return self._make_request("POST", "api/tags/", json=payload)
    
    def set_document_tags(self, document_id: int, tag_ids: List[int]) -> Dict[str, Any]:
        """
        Set the complete list of tags for a document.
        
        Paperless does NOT support incremental tag updates - this replaces the entire tag list.
        
        Args:
            document_id: The Paperless document ID
            tag_ids: Complete list of tag IDs to assign to the document
            
        Returns:
            The updated document object
        """
        payload = {"tags": tag_ids}
        return self._make_request("PATCH", f"api/documents/{document_id}/", json=payload)
    
    def add_tag(self, document_id: int, tag_id: int) -> Dict[str, Any]:
        """
        Add a single tag to a document.
        
        This is a convenience method that:
        1. Fetches the current document
        2. Reads its current tag IDs
        3. Adds the new tag ID if not already present
        4. PATCHes the complete updated tag list
        
        Args:
            document_id: The Paperless document ID
            tag_id: The tag ID to add
            
        Returns:
            The updated document object
        """
        # Get current document
        doc = self.get_document(document_id)
        
        # Get current tag IDs
        current_tag_ids = [tag.get("id") for tag in doc.get("tags", []) if isinstance(tag, dict) and tag.get("id")]
        
        # Add the new tag if not already present
        if tag_id not in current_tag_ids:
            current_tag_ids.append(tag_id)
        
        # Set the complete tag list
        return self.set_document_tags(document_id, current_tag_ids)
    
    def remove_tag(self, document_id: int, tag_id: int) -> Dict[str, Any]:
        """
        Remove a single tag from a document.
        
        This is a convenience method that:
        1. Fetches the current document
        2. Reads its current tag IDs
        3. Removes the specified tag ID
        4. PATCHes the complete updated tag list
        
        Args:
            document_id: The Paperless document ID
            tag_id: The tag ID to remove
            
        Returns:
            The updated document object
        """
        # Get current document
        doc = self.get_document(document_id)
        
        # Get current tag IDs
        current_tag_ids = [tag.get("id") for tag in doc.get("tags", []) if isinstance(tag, dict) and tag.get("id")]
        
        # Remove the specified tag if present
        if tag_id in current_tag_ids:
            current_tag_ids.remove(tag_id)
        
        # Set the complete tag list
        return self.set_document_tags(document_id, current_tag_ids)
    
    def list_correspondents(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        List all correspondents.
        
        Args:
            page: Page number (default: 1)
            page_size: Number of results per page (default: 100)
            
        Returns:
            Dictionary with correspondents and pagination info
        """
        params = {"page": page, "page_size": page_size}
        return self._make_request("GET", "api/correspondents/", params=params)
    
    def list_all_correspondents(self) -> List[Dict[str, Any]]:
        """
        Get all correspondents, handling pagination automatically.
        
        Returns:
            List of all correspondent objects
        """
        all_correspondents = []
        page = 1
        
        while True:
            response = self.list_correspondents(page=page, page_size=100)
            results = response.get("results", [])
            all_correspondents.extend(results)
            
            if not response.get("next"):
                break
            
            page += 1
            if page > 50:
                logger.warning("Reached maximum page count (50) while fetching correspondents")
                break
        
        return all_correspondents
    
    def list_document_types(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        List all document types.
        
        Args:
            page: Page number (default: 1)
            page_size: Number of results per page (default: 100)
            
        Returns:
            Dictionary with document types and pagination info
        """
        params = {"page": page, "page_size": page_size}
        return self._make_request("GET", "api/document_types/", params=params)
    
    def list_all_document_types(self) -> List[Dict[str, Any]]:
        """
        Get all document types, handling pagination automatically.
        
        Returns:
            List of all document type objects
        """
        all_types = []
        page = 1
        
        while True:
            response = self.list_document_types(page=page, page_size=100)
            results = response.get("results", [])
            all_types.extend(results)
            
            if not response.get("next"):
                break
            
            page += 1
            if page > 50:
                logger.warning("Reached maximum page count (50) while fetching document types")
                break
        
        return all_types
    
    def list_documents(self, 
                       page: int = 1, 
                       page_size: int = 100,
                       tag_ids: Optional[List[int]] = None,
                       correspondent_ids: Optional[List[int]] = None,
                       document_type_ids: Optional[List[int]] = None,
                       ordering: str = "-created") -> Dict[str, Any]:
        """
        List documents with optional filtering.
        
        Args:
            page: Page number (default: 1)
            page_size: Number of results per page (default: 100)
            tag_ids: Filter by tag IDs
            correspondent_ids: Filter by correspondent IDs
            document_type_ids: Filter by document type IDs
            ordering: Ordering for results (default: "-created" for newest first)
            
        Returns:
            Dictionary with documents and pagination info
        """
        params = {
            "page": page,
            "page_size": page_size,
            "ordering": ordering,
        }
        
        if tag_ids:
            # Convert tag IDs to comma-separated string
            # Paperless-ngx uses tags__id__in for filtering by tag IDs
            params["tags__id__in"] = ",".join(map(str, tag_ids))
        
        if correspondent_ids:
            params["correspondent__id__in"] = ",".join(map(str, correspondent_ids))
        
        if document_type_ids:
            params["document_type__id__in"] = ",".join(map(str, document_type_ids))
        
        return self._make_request("GET", "api/documents/", params=params)
    
    def list_all_documents(self,
                           tag_ids: Optional[List[int]] = None,
                           correspondent_ids: Optional[List[int]] = None,
                           document_type_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Get all documents with optional filtering, handling pagination automatically.
        
        Args:
            tag_ids: Filter by tag IDs
            correspondent_ids: Filter by correspondent IDs
            document_type_ids: Filter by document type IDs
            
        Returns:
            List of all document objects matching the filters
        """
        all_documents = []
        page = 1
        
        while True:
            response = self.list_documents(
                page=page, 
                page_size=100,
                tag_ids=tag_ids,
                correspondent_ids=correspondent_ids,
                document_type_ids=document_type_ids
            )
            results = response.get("results", [])
            all_documents.extend(results)
            
            if not response.get("next"):
                break
            
            page += 1
            if page > 100:  # Safety limit for large document collections
                logger.warning("Reached maximum page count (100) while fetching documents")
                break
        
        return all_documents
    
    def get_document(self, document_id: int) -> Dict[str, Any]:
        """
        Get a single document by its ID.
        
        Args:
            document_id: The Paperless document ID
            
        Returns:
            Document object
        """
        return self._make_request("GET", f"api/documents/{document_id}/")
    
    def get_document_content(self, document_id: int, page: int = 1) -> Dict[str, Any]:
        """
        Get the content (OCR text) of a document.
        
        Args:
            document_id: The Paperless document ID
            page: Page number for multi-page documents (default: 1)
            
        Returns:
            Dictionary containing the document content
        """
        return self._make_request("GET", f"api/documents/{document_id}/content/", params={"page": page})
    
    def get_document_full_text(self, document_id: int) -> str:
        """
        Get the full OCR text content for a document.
        
        This handles multi-page documents by concatenating all pages.
        
        Args:
            document_id: The Paperless document ID
            
        Returns:
            Full text content of the document
        """
        # First, get document info to see how many pages
        doc_info = self.get_document(document_id)
        page_count = doc_info.get("page_count", 1)
        
        full_text = ""
        
        for page in range(1, page_count + 1):
            content_response = self.get_document_content(document_id, page)
            page_content = content_response.get("content", "")
            if page_content:
                if full_text:
                    full_text += "\n\n---\n\n"  # Separate pages
                full_text += page_content
        
        return full_text
    
    def download_document(self, document_id: int, filename: Optional[str] = None) -> bytes:
        """
        Download the original document file.
        
        Args:
            document_id: The Paperless document ID
            filename: Optional filename parameter (not commonly used in Paperless-ngx)
            
        Returns:
            Raw bytes of the document file
        """
        params = {}
        if filename:
            params["filename"] = filename
            
        # Use the original file endpoint
        endpoint = f"api/documents/{document_id}/download/"
        
        try:
            response = self.session.get(
                urljoin(f"{self.base_url}/", endpoint),
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code >= 400:
                error_msg = f"Paperless API error {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            return response.content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download document {document_id}: {str(e)}")
            raise
    
    def get_document_metadata(self, document_id: int) -> Dict[str, Any]:
        """
        Get metadata for a document suitable for Loseme indexing.
        
        Args:
            document_id: The Paperless document ID
            
        Returns:
            Dictionary containing metadata for the document
        """
        doc_info = self.get_document(document_id)
        
        def get_name_or_id(field_value: Any) -> tuple:
            """Helper to extract name and id from a field that might be an int or a dict."""
            if field_value is None:
                return None, None
            if isinstance(field_value, dict):
                return field_value.get("name"), field_value.get("id")
            elif isinstance(field_value, int):
                return None, field_value
            else:
                return field_value, None
        
        correspondent_name, correspondent_id = get_name_or_id(doc_info.get("correspondent"))
        document_type_name, document_type_id = get_name_or_id(doc_info.get("document_type"))
        
        # Extract relevant metadata
        metadata = {
            "paperless_document_id": doc_info.get("id"),
            "title": doc_info.get("title", ""),
            "original_filename": doc_info.get("original_file_name", ""),
            "created": doc_info.get("created"),
            "modified": doc_info.get("modified"),
            "added": doc_info.get("added"),
            "content_type": doc_info.get("mime_type", "application/octet-stream"),
            "page_count": doc_info.get("page_count", 1),
            "file_size": doc_info.get("file_size"),
            "checksum": doc_info.get("checksum"),
            
            # Extract tag information
            "tags": [tag.get("name") for tag in doc_info.get("tags", []) if isinstance(tag, dict)],
            "tag_ids": [tag.get("id") for tag in doc_info.get("tags", []) if isinstance(tag, dict)],
            
            # Extract correspondent information
            "correspondent": correspondent_name,
            "correspondent_id": correspondent_id,
            
            # Extract document type information
            "document_type": document_type_name,
            "document_type_id": document_type_id,
            
            # Storage path (for reference)
            "storage_path": doc_info.get("storage_path"),
        }
        
        return metadata
    
    def get_document_for_ingestion(self, document_id: int) -> Dict[str, Any]:
        """
        Get a document with all the information needed for Loseme ingestion.
        
        This combines metadata and content extraction into a single call.
        
        Args:
            document_id: The Paperless document ID
            
        Returns:
            Dictionary containing all document information for ingestion
        """
        metadata = self.get_document_metadata(document_id)
        
        # Get the full text content
        text_content = self.get_document_full_text(document_id)
        
        # Add content to metadata
        metadata["text"] = text_content
        
        # Use modified timestamp as the fingerprint for change detection
        metadata["fingerprint"] = metadata.get("modified", "")
        
        return metadata
    
    def get_documents_changed_since(self, 
                                    since_timestamp: datetime,
                                    tag_ids: Optional[List[int]] = None,
                                    correspondent_ids: Optional[List[int]] = None,
                                    document_type_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Get documents that have been modified since a specific timestamp.
        
        This is useful for incremental sync.
        
        Args:
            since_timestamp: Only return documents modified after this timestamp
            tag_ids: Filter by tag IDs
            correspondent_ids: Filter by correspondent IDs
            document_type_ids: Filter by document type IDs
            
        Returns:
            List of document objects that have changed since the timestamp
        """
        # Get all documents (this could be optimized with server-side filtering if available)
        all_docs = self.list_all_documents(
            tag_ids=tag_ids,
            correspondent_ids=correspondent_ids,
            document_type_ids=document_type_ids
        )
        
        # Filter by modified date
        since_iso = since_timestamp.isoformat()
        changed_docs = []
        
        for doc in all_docs:
            doc_modified = doc.get("modified")
            if doc_modified and doc_modified > since_iso:
                changed_docs.append(doc)
        
        return changed_docs
