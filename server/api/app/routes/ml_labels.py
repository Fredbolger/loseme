"""
ML Labels API endpoints for LoSeMe server.

This module provides RESTful endpoints for managing ML labels:
- Label definitions (schema)
- Label options (allowed values for select/multiselect)
- Document label assignments

All endpoints are prefixed with /ml-labels and require API key authentication.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from storage.metadata_db.ml_labels import (
    # Definitions
    create_label_definition,
    list_label_definitions,
    get_label_definition,
    update_label_definition,
    delete_label_definition,
    # Options
    create_label_option,
    list_label_options,
    delete_label_option,
    # Assignments
    assign_label,
    remove_label_assignment,
    get_labels_for_document,
    list_documents_by_label,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml-labels", tags=["ml_labels"])


# =============================================================================
# Request/Response Models
# =============================================================================

# Label Definition Models
class LabelDefinitionCreateRequest(BaseModel):
    key: str = Field(..., description="Machine slug, e.g. 'sentiment'")
    name: str = Field(..., description="Display name, e.g. 'Sentiment'")
    value_type: str = Field(..., description="One of: select, multiselect, text, boolean, number")
    description: Optional[str] = Field(None, description="Optional description")
    color: Optional[str] = Field(None, description="Optional default color swatch")


class LabelDefinitionUpdateRequest(BaseModel):
    key: Optional[str] = Field(None, description="Machine slug")
    name: Optional[str] = Field(None, description="Display name")
    description: Optional[str] = Field(None, description="Description")
    value_type: Optional[str] = Field(None, description="Value type")
    color: Optional[str] = Field(None, description="Default color swatch")
    is_active: Optional[bool] = Field(None, description="Whether the definition is active")


class LabelDefinitionResponse(BaseModel):
    id: str
    key: str
    name: str
    description: Optional[str] = None
    value_type: str
    color: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str


# Label Option Models
class LabelOptionCreateRequest(BaseModel):
    value: str = Field(..., description="Machine value, e.g. 'positive'")
    display_name: str = Field(..., description="Display name, e.g. 'Positive'")
    color: Optional[str] = Field(None, description="Optional color for this option")
    sort_order: int = Field(0, description="Sort order (default 0)")


class LabelOptionResponse(BaseModel):
    id: str
    definition_id: str
    value: str
    display_name: str
    color: Optional[str] = None
    sort_order: int


# Document Label Assignment Models
class DocumentLabelAssignRequest(BaseModel):
    definition_id: str = Field(..., description="The label definition ID")
    option_id: Optional[str] = Field(None, description="For select/multiselect: the option ID")
    text_value: Optional[str] = Field(None, description="For text type: the text value")
    number_value: Optional[float] = Field(None, description="For number type: the numeric value")
    bool_value: Optional[bool] = Field(None, description="For boolean type: the boolean value")
    confidence: Optional[float] = Field(None, description="Confidence score (0..1 for model predictions)")
    label_source: str = Field("human", description="Either 'human' or 'model'")


class DocumentLabelResponse(BaseModel):
    id: str
    document_part_id: str
    definition_id: str
    option_id: Optional[str] = None
    text_value: Optional[str] = None
    number_value: Optional[float] = None
    bool_value: Optional[bool] = None
    confidence: Optional[float] = None
    label_source: str
    created_at: str
    updated_at: str
    # Joined fields for display convenience
    definition_key: Optional[str] = None
    definition_name: Optional[str] = None
    definition_value_type: Optional[str] = None
    definition_color: Optional[str] = None
    option_value: Optional[str] = None
    option_display_name: Optional[str] = None
    option_color: Optional[str] = None


# =============================================================================
# Label Definition Endpoints
# =============================================================================

@router.post("/definitions", response_model=LabelDefinitionResponse)
async def create_definition(request: LabelDefinitionCreateRequest):
    """
    Create a new label definition.
    
    The key must be unique across all definitions.
    """
    logger.debug(f"Creating label definition with key '{request.key}'")
    
    try:
        definition = create_label_definition(
            key=request.key,
            name=request.name,
            value_type=request.value_type,
            description=request.description,
            color=request.color,
        )
        logger.info(f"Created label definition {definition['id']}")
        return definition
    except ValueError as e:
        logger.error(f"Validation error creating label definition: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/definitions", response_model=List[LabelDefinitionResponse])
async def list_definitions(active_only: bool = Query(True, description="Only return active definitions")):
    """
    List all label definitions.
    
    Can be filtered to only active definitions.
    """
    logger.debug(f"Listing label definitions (active_only={active_only})")
    
    definitions = list_label_definitions(active_only=active_only)
    logger.info(f"Retrieved {len(definitions)} label definitions")
    return definitions


@router.get("/definitions/{definition_id}", response_model=LabelDefinitionResponse)
async def get_definition(definition_id: str):
    """
    Get a single label definition by ID.
    """
    logger.debug(f"Getting label definition {definition_id}")
    
    definition = get_label_definition(definition_id)
    if definition is None:
        logger.error(f"Label definition {definition_id} not found")
        raise HTTPException(status_code=404, detail="Label definition not found")
    
    logger.info(f"Retrieved label definition {definition_id}")
    return definition


@router.put("/definitions/{definition_id}", response_model=LabelDefinitionResponse)
async def update_definition(definition_id: str, request: LabelDefinitionUpdateRequest):
    """
    Update an existing label definition.
    
    Only provided fields are updated. Cannot update id or created_at.
    """
    logger.debug(f"Updating label definition {definition_id}")
    
    definition = get_label_definition(definition_id)
    if definition is None:
        logger.error(f"Label definition {definition_id} not found for update")
        raise HTTPException(status_code=404, detail="Label definition not found")
    
    # Convert is_active to int for SQL
    fields = request.dict(exclude_unset=True)
    if 'is_active' in fields:
        fields['is_active'] = int(fields['is_active'])
    
    try:
        updated = update_label_definition(definition_id, **fields)
        if updated is None:
            raise HTTPException(status_code=404, detail="Label definition not found")
        logger.info(f"Updated label definition {definition_id}")
        return updated
    except ValueError as e:
        logger.error(f"Validation error updating label definition: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/definitions/{definition_id}")
async def delete_definition(definition_id: str):
    """
    Delete a label definition.
    
    This cascades to delete all options and assignments for this definition.
    The operation cannot be undone.
    """
    logger.debug(f"Deleting label definition {definition_id}")
    
    definition = get_label_definition(definition_id)
    if definition is None:
        logger.error(f"Label definition {definition_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Label definition not found")
    
    success = delete_label_definition(definition_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete label definition")
    
    logger.info(f"Deleted label definition {definition_id}")
    return {"status": "deleted", "definition_id": definition_id}


# =============================================================================
# Label Option Endpoints
# =============================================================================

@router.post("/definitions/{definition_id}/options", response_model=LabelOptionResponse)
async def create_option(definition_id: str, request: LabelOptionCreateRequest):
    """
    Create a new option for a select/multiselect label definition.
    
    The value must be unique within the definition.
    """
    logger.debug(f"Creating label option for definition {definition_id}")
    
    definition = get_label_definition(definition_id)
    if definition is None:
        logger.error(f"Label definition {definition_id} not found")
        raise HTTPException(status_code=404, detail="Label definition not found")
    
    if definition['value_type'] not in ('select', 'multiselect'):
        logger.error(f"Cannot add options to non-select definition (type: {definition['value_type']})")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot add options to non-select definition (type: {definition['value_type']})"
        )
    
    try:
        option = create_label_option(
            definition_id=definition_id,
            value=request.value,
            display_name=request.display_name,
            color=request.color,
            sort_order=request.sort_order,
        )
        logger.info(f"Created label option {option['id']} for definition {definition_id}")
        return option
    except ValueError as e:
        logger.error(f"Validation error creating label option: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/definitions/{definition_id}/options", response_model=List[LabelOptionResponse])
async def list_options(definition_id: str):
    """
    List all options for a label definition.
    """
    logger.debug(f"Listing options for definition {definition_id}")
    
    definition = get_label_definition(definition_id)
    if definition is None:
        logger.error(f"Label definition {definition_id} not found")
        raise HTTPException(status_code=404, detail="Label definition not found")
    
    options = list_label_options(definition_id)
    logger.info(f"Retrieved {len(options)} options for definition {definition_id}")
    return options


@router.delete("/options/{option_id}")
async def delete_option(option_id: str):
    """
    Delete a label option.
    
    This will also delete any document assignments using this option.
    """
    logger.debug(f"Deleting label option {option_id}")
    
    success = delete_label_option(option_id)
    if not success:
        logger.error(f"Label option {option_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Label option not found")
    
    logger.info(f"Deleted label option {option_id}")
    return {"status": "deleted", "option_id": option_id}


# =============================================================================
# Document Label Assignment Endpoints
# =============================================================================

@router.get("/documents/{document_part_id}", response_model=List[DocumentLabelResponse])
async def get_document_labels(document_part_id: str):
    """
    Get all label assignments for a document.
    
    Returns assignments joined with definition and option info for display.
    """
    logger.debug(f"Getting labels for document {document_part_id}")
    
    labels = get_labels_for_document(document_part_id)
    logger.info(f"Retrieved {len(labels)} labels for document {document_part_id}")
    return labels


@router.post("/documents/{document_part_id}", response_model=DocumentLabelResponse)
async def assign_document_label(
    document_part_id: str,
    request: DocumentLabelAssignRequest
):
    """
    Assign a label to a document.
    
    For single-valued types (select, text, number, boolean), this replaces
    any existing assignment for this definition. For multiselect, this adds
    or updates the specific option assignment.
    """
    logger.debug(f"Assigning label to document {document_part_id}")
    
    try:
        assignment = assign_label(
            document_part_id=document_part_id,
            definition_id=request.definition_id,
            option_id=request.option_id,
            text_value=request.text_value,
            number_value=request.number_value,
            bool_value=request.bool_value,
            confidence=request.confidence,
            label_source=request.label_source,
        )
        logger.info(f"Assigned label {assignment['id']} to document {document_part_id}")
        return assignment
    except ValueError as e:
        logger.error(f"Validation error assigning label: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/documents/{document_part_id}/{assignment_id}")
async def remove_document_label(
    document_part_id: str,
    assignment_id: str
):
    """
    Remove a label assignment from a document.
    """
    logger.debug(f"Removing label assignment {assignment_id} from document {document_part_id}")
    
    success = remove_label_assignment(assignment_id)
    if not success:
        logger.error(f"Label assignment {assignment_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Label assignment not found")
    
    logger.info(f"Deleted label assignment {assignment_id}")
    return {"status": "deleted", "assignment_id": assignment_id}


@router.get("/documents-by-label/{definition_id}")
async def list_documents_with_label(
    definition_id: str,
    option_id: Optional[str] = Query(None, description="Filter by specific option ID")
):
    """
    List all document_part_ids that have a specific label.
    
    Can be filtered by option_id for select/multiselect definitions.
    """
    logger.debug(f"Listing documents with label definition {definition_id}")
    
    definition = get_label_definition(definition_id)
    if definition is None:
        logger.error(f"Label definition {definition_id} not found")
        raise HTTPException(status_code=404, detail="Label definition not found")
    
    document_ids = list_documents_by_label(definition_id, option_id)
    logger.info(f"Retrieved {len(document_ids)} documents with label {definition_id}")
    return {"document_part_ids": document_ids}
