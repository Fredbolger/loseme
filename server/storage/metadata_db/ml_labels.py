"""
ML Labels Storage Module

Generic labeling engine for LoSeMe. This module provides CRUD operations for:
- Label definitions (the schema of a label dimension)
- Label options (allowed values for select/multiselect definitions)
- Document label assignments

# EXTENDING THIS SYSTEM
# ----------------------
# To add a new label dimension (e.g. "urgency"):
#   1. POST /ml-labels/definitions {"key": "urgency", "name": "Urgency",
#      "value_type": "select"}
#   2. POST /ml-labels/definitions/{id}/options for each allowed value
#   3. Done — it now shows up in the Labels tab and the document assigner
#      automatically. No code changes needed.

Cardinality rule (enforced in this layer, not SQL):
For `select` / `text` / `number` / `boolean` definitions, a document may have
at most one row per `definition_id` (upsert: delete-then-insert on assign).
For `multiselect`, multiple rows per `definition_id` are allowed (one per selected option).
"""

import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid
import logging

from storage.metadata_db.db import get_connection, execute, fetch_one, fetch_all

logger = logging.getLogger(__name__)

# =============================================================================
# Label Definitions
# =============================================================================

def create_label_definition(
    key: str,
    name: str,
    value_type: str,
    description: Optional[str] = None,
    color: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new label definition.
    
    Args:
        key: Machine slug, e.g. "sentiment"
        name: Display name, e.g. "Sentiment"
        value_type: One of 'select', 'multiselect', 'text', 'boolean', 'number'
        description: Optional description
        color: Optional default color swatch
        
    Returns:
        The created label definition as a dictionary
    """
    definition_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Validate value_type
    valid_types = {'select', 'multiselect', 'text', 'boolean', 'number'}
    if value_type not in valid_types:
        raise ValueError(f"Invalid value_type: {value_type}. Must be one of {valid_types}")
    
    query = """
    INSERT INTO ml_label_definitions (id, key, name, description, value_type, color, is_active, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
    """
    
    with get_connection() as conn:
        conn.execute(query, (definition_id, key, name, description, value_type, color, now, now))
        conn.commit()
    
    logger.info(f"Created label definition {definition_id} with key '{key}'")
    
    return {
        "id": definition_id,
        "key": key,
        "name": name,
        "description": description,
        "value_type": value_type,
        "color": color,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


def list_label_definitions(active_only: bool = True) -> List[Dict[str, Any]]:
    """
    List all label definitions.
    
    Args:
        active_only: If True, only return active definitions
        
    Returns:
        List of label definition dictionaries
    """
    query = "SELECT * FROM ml_label_definitions"
    params: tuple = ()
    
    if active_only:
        query += " WHERE is_active = 1"
    
    query += " ORDER BY created_at DESC"
    
    rows = fetch_all(query, params)
    
    return [dict(row) for row in rows]


def get_label_definition(definition_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a label definition by ID.
    
    Args:
        definition_id: The ID of the label definition
        
    Returns:
        The label definition as a dictionary, or None if not found
    """
    query = "SELECT * FROM ml_label_definitions WHERE id = ?"
    row = fetch_one(query, (definition_id,))
    
    if row is None:
        logger.debug(f"Label definition with ID {definition_id} not found")
        return None
    
    return dict(row)


def get_label_definition_by_key(key: str) -> Optional[Dict[str, Any]]:
    """
    Get a label definition by its key.
    
    Args:
        key: The machine slug key
        
    Returns:
        The label definition as a dictionary, or None if not found
    """
    query = "SELECT * FROM ml_label_definitions WHERE key = ?"
    row = fetch_one(query, (key,))
    
    if row is None:
        logger.debug(f"Label definition with key '{key}' not found")
        return None
    
    return dict(row)


def update_label_definition(definition_id: str, **fields) -> Optional[Dict[str, Any]]:
    """
    Update an existing label definition.
    
    Args:
        definition_id: The ID of the label definition to update
        **fields: Fields to update (key, name, description, value_type, color, is_active)
        
    Returns:
        The updated label definition as a dictionary, or None if not found
    """
    # Get the existing definition
    existing = get_label_definition(definition_id)
    if existing is None:
        logger.warning(f"Cannot update label definition with ID {definition_id}: not found")
        return None
    
    # Validate value_type if being updated
    if 'value_type' in fields:
        valid_types = {'select', 'multiselect', 'text', 'boolean', 'number'}
        if fields['value_type'] not in valid_types:
            raise ValueError(f"Invalid value_type: {fields['value_type']}. Must be one of {valid_types}")
    
    # Build the update query dynamically based on provided fields
    updated_at = datetime.now(timezone.utc).isoformat()
    fields['updated_at'] = updated_at
    
    # Remove fields that shouldn't be updated
    fields.pop('id', None)
    fields.pop('created_at', None)
    
    if not fields:
        return existing
    
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    query = f"UPDATE ml_label_definitions SET {set_clause} WHERE id = ?"
    params = tuple(fields.values()) + (definition_id,)
    
    with get_connection() as conn:
        conn.execute(query, params)
        conn.commit()
    
    logger.info(f"Updated label definition {definition_id}")
    
    # Return the updated definition
    return get_label_definition(definition_id)


def delete_label_definition(definition_id: str) -> bool:
    """
    Delete a label definition. This cascades to delete options and assignments.
    
    Args:
        definition_id: The ID of the label definition to delete
        
    Returns:
        True if the definition was deleted, False if not found
    """
    # First check if it exists
    existing = get_label_definition(definition_id)
    if existing is None:
        logger.warning(f"Cannot delete label definition with ID {definition_id}: not found")
        return False
    
    query = "DELETE FROM ml_label_definitions WHERE id = ?"
    
    with get_connection() as conn:
        conn.execute(query, (definition_id,))
        conn.commit()
    
    logger.info(f"Deleted label definition {definition_id} (cascades to options and assignments)")
    return True


# =============================================================================
# Label Options
# =============================================================================

def create_label_option(
    definition_id: str,
    value: str,
    display_name: str,
    color: Optional[str] = None,
    sort_order: int = 0,
) -> Dict[str, Any]:
    """
    Create a new label option for a select/multiselect definition.
    
    Args:
        definition_id: The ID of the parent label definition
        value: Machine value, e.g. "positive"
        display_name: Display name, e.g. "Positive"
        color: Optional color for this option
        sort_order: Sort order (default 0)
        
    Returns:
        The created label option as a dictionary
    """
    # Verify the parent definition exists and is select/multiselect
    definition = get_label_definition(definition_id)
    if definition is None:
        raise ValueError(f"Label definition with ID {definition_id} not found")
    
    if definition['value_type'] not in ('select', 'multiselect'):
        raise ValueError(f"Cannot add options to non-select definition (type: {definition['value_type']})")
    
    option_id = str(uuid.uuid4())
    
    query = """
    INSERT INTO ml_label_options (id, definition_id, value, display_name, color, sort_order)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    
    with get_connection() as conn:
        try:
            conn.execute(query, (option_id, definition_id, value, display_name, color, sort_order))
            conn.commit()
        except sqlite3.IntegrityError as e:
            # Handle unique constraint violation (definition_id, value)
            raise ValueError(f"Option with value '{value}' already exists for this definition")
    
    logger.info(f"Created label option {option_id} for definition {definition_id}")
    
    return {
        "id": option_id,
        "definition_id": definition_id,
        "value": value,
        "display_name": display_name,
        "color": color,
        "sort_order": sort_order,
    }


def list_label_options(definition_id: str) -> List[Dict[str, Any]]:
    """
    List all label options for a definition.
    
    Args:
        definition_id: The ID of the label definition
        
    Returns:
        List of label option dictionaries, ordered by sort_order
    """
    query = """
    SELECT * FROM ml_label_options 
    WHERE definition_id = ? 
    ORDER BY sort_order ASC, display_name ASC
    """
    rows = fetch_all(query, (definition_id,))
    
    return [dict(row) for row in rows]


def get_label_option(option_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a label option by ID.
    
    Args:
        option_id: The ID of the label option
        
    Returns:
        The label option as a dictionary, or None if not found
    """
    query = "SELECT * FROM ml_label_options WHERE id = ?"
    row = fetch_one(query, (option_id,))
    
    if row is None:
        logger.debug(f"Label option with ID {option_id} not found")
        return None
    
    return dict(row)


def delete_label_option(option_id: str) -> bool:
    """
    Delete a label option.
    
    Args:
        option_id: The ID of the label option to delete
        
    Returns:
        True if the option was deleted, False if not found
    """
    # First check if it exists
    existing = get_label_option(option_id)
    if existing is None:
        logger.warning(f"Cannot delete label option with ID {option_id}: not found")
        return False
    
    query = "DELETE FROM ml_label_options WHERE id = ?"
    
    with get_connection() as conn:
        conn.execute(query, (option_id,))
        conn.commit()
    
    logger.info(f"Deleted label option {option_id}")
    return True


# =============================================================================
# Document Label Assignments
# =============================================================================

def assign_label(
    document_part_id: str,
    definition_id: str,
    *,
    option_id: Optional[str] = None,
    text_value: Optional[str] = None,
    number_value: Optional[float] = None,
    bool_value: Optional[bool] = None,
    confidence: Optional[float] = None,
    label_source: str = "human",
) -> Dict[str, Any]:
    """
    Assign a label to a document.
    
    For single-valued types (select, text, number, boolean): deletes existing
    (document_part_id, definition_id) row(s) first, then inserts the new one.
    
    For multiselect: only deletes the specific (document_part_id, definition_id, option_id)
    if re-assigning the same option.
    
    Args:
        document_part_id: The document part ID
        definition_id: The label definition ID
        option_id: For select/multiselect, the option ID
        text_value: For text type, the text value
        number_value: For number type, the numeric value
        bool_value: For boolean type, the boolean value
        confidence: Optional confidence score (0..1 for model predictions, NULL for human)
        label_source: Either 'human' or 'model'
        
    Returns:
        The created label assignment as a dictionary
    """
    # Validate label_source
    if label_source not in ('human', 'model'):
        raise ValueError(f"Invalid label_source: {label_source}. Must be 'human' or 'model'")
    
    # Validate confidence
    if confidence is not None and (confidence < 0 or confidence > 1):
        raise ValueError(f"Invalid confidence: {confidence}. Must be between 0 and 1")
    
    # Get the definition to determine the value type
    definition = get_label_definition(definition_id)
    if definition is None:
        raise ValueError(f"Label definition with ID {definition_id} not found")
    
    value_type = definition['value_type']
    
    # Validate that the provided value matches the definition type
    if value_type == 'select':
        if option_id is None:
            raise ValueError("select type requires option_id")
    elif value_type == 'multiselect':
        if option_id is None:
            raise ValueError("multiselect type requires option_id")
    elif value_type == 'text':
        if text_value is None:
            raise ValueError("text type requires text_value")
    elif value_type == 'number':
        if number_value is None:
            raise ValueError("number type requires number_value")
    elif value_type == 'boolean':
        if bool_value is None:
            raise ValueError("boolean type requires bool_value")
    
    assignment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # For single-valued types, delete existing assignments first
    if value_type in ('select', 'text', 'number', 'boolean'):
        delete_query = "DELETE FROM ml_document_labels WHERE document_part_id = ? AND definition_id = ?"
        with get_connection() as conn:
            conn.execute(delete_query, (document_part_id, definition_id))
            conn.commit()
    # For multiselect with the same option_id, delete the specific assignment
    elif value_type == 'multiselect' and option_id:
        delete_query = """
        DELETE FROM ml_document_labels 
        WHERE document_part_id = ? AND definition_id = ? AND option_id = ?
        """
        with get_connection() as conn:
            conn.execute(delete_query, (document_part_id, definition_id, option_id))
            conn.commit()
    
    # Build the insert query based on the value type
    if value_type in ('select', 'multiselect'):
        insert_query = """
        INSERT INTO ml_document_labels (id, document_part_id, definition_id, option_id, confidence, label_source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (assignment_id, document_part_id, definition_id, option_id, confidence, label_source, now, now)
    elif value_type == 'text':
        insert_query = """
        INSERT INTO ml_document_labels (id, document_part_id, definition_id, text_value, confidence, label_source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (assignment_id, document_part_id, definition_id, text_value, confidence, label_source, now, now)
    elif value_type == 'number':
        insert_query = """
        INSERT INTO ml_document_labels (id, document_part_id, definition_id, number_value, confidence, label_source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (assignment_id, document_part_id, definition_id, number_value, confidence, label_source, now, now)
    elif value_type == 'boolean':
        insert_query = """
        INSERT INTO ml_document_labels (id, document_part_id, definition_id, bool_value, confidence, label_source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (assignment_id, document_part_id, definition_id, int(bool_value), confidence, label_source, now, now)
    else:
        raise ValueError(f"Unknown value_type: {value_type}")
    
    with get_connection() as conn:
        conn.execute(insert_query, params)
        conn.commit()
    
    logger.info(f"Assigned label {assignment_id} to document {document_part_id}")
    
    return {
        "id": assignment_id,
        "document_part_id": document_part_id,
        "definition_id": definition_id,
        "option_id": option_id,
        "text_value": text_value,
        "number_value": number_value,
        "bool_value": bool_value,
        "confidence": confidence,
        "label_source": label_source,
        "created_at": now,
        "updated_at": now,
    }


def remove_label_assignment(assignment_id: str) -> bool:
    """
    Remove a label assignment.
    
    Args:
        assignment_id: The ID of the label assignment to remove
        
    Returns:
        True if the assignment was removed, False if not found
    """
    # First check if it exists
    existing = get_label_assignment(assignment_id)
    if existing is None:
        logger.warning(f"Cannot delete label assignment with ID {assignment_id}: not found")
        return False
    
    query = "DELETE FROM ml_document_labels WHERE id = ?"
    
    with get_connection() as conn:
        conn.execute(query, (assignment_id,))
        conn.commit()
    
    logger.info(f"Deleted label assignment {assignment_id}")
    return True


def get_label_assignment(assignment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a label assignment by ID.
    
    Args:
        assignment_id: The ID of the label assignment
        
    Returns:
        The label assignment as a dictionary, or None if not found
    """
    query = "SELECT * FROM ml_document_labels WHERE id = ?"
    row = fetch_one(query, (assignment_id,))
    
    if row is None:
        return None
    
    return dict(row)


def get_labels_for_document(document_part_id: str) -> List[Dict[str, Any]]:
    """
    Get all label assignments for a document, joined with definition and option info.
    
    Args:
        document_part_id: The document part ID
        
    Returns:
        List of label assignment dictionaries with joined definition and option data
    """
    query = """
    SELECT 
        dl.*,
        d.key as definition_key,
        d.name as definition_name,
        d.value_type as definition_value_type,
        d.color as definition_color,
        o.value as option_value,
        o.display_name as option_display_name,
        o.color as option_color
    FROM ml_document_labels dl
    LEFT JOIN ml_label_definitions d ON dl.definition_id = d.id
    LEFT JOIN ml_label_options o ON dl.option_id = o.id
    WHERE dl.document_part_id = ?
    ORDER BY d.name ASC, o.sort_order ASC
    """
    rows = fetch_all(query, (document_part_id,))
    
    return [dict(row) for row in rows]


def list_documents_by_label(definition_id: str, option_id: Optional[str] = None) -> List[str]:
    """
    List all document_part_ids that have a specific label.
    
    Args:
        definition_id: The label definition ID
        option_id: Optional - if provided, filter by this specific option
        
    Returns:
        List of document_part_id strings
    """
    if option_id:
        query = """
        SELECT DISTINCT document_part_id 
        FROM ml_document_labels 
        WHERE definition_id = ? AND option_id = ?
        """
        params = (definition_id, option_id)
    else:
        query = """
        SELECT DISTINCT document_part_id 
        FROM ml_document_labels 
        WHERE definition_id = ?
        """
        params = (definition_id,)
    
    rows = fetch_all(query, params)
    
    return [row['document_part_id'] for row in rows]


def get_label_statistics(definition_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get label assignment statistics grouped by option for each definition.
    
    Args:
        definition_id: Optional - if provided, get stats only for this definition
                        If None, get stats for all definitions
    
    Returns:
        List of dictionaries with:
        - definition_id: The label definition ID
        - definition_key: The definition key
        - definition_name: The definition name
        - definition_value_type: The value type
        - option_id: The option ID (for select/multiselect)
        - option_value: The option value (for select/multiselect) or actual value (for text/boolean/number)
        - option_display_name: The option display name (for select/multiselect) or actual value (for text/boolean/number)
        - option_color: The option color (for select/multiselect)
        - count: Number of documents with this label
        - total: Total number of documents with this definition (for percentage calculation)
    """
    result: List[Dict[str, Any]] = []
    
    if definition_id:
        definitions_filter = "AND d.id = ?"
        params_base: tuple = (definition_id,)
        order_by = "ORDER BY o.sort_order ASC, o.display_name ASC"
    else:
        definitions_filter = ""
        params_base = ()
        order_by = "ORDER BY d.name ASC, o.sort_order ASC, o.display_name ASC"
    
    # Handle select/multiselect definitions (group by option_id)
    option_query = f"""
    SELECT 
        dl.definition_id,
        d.key as definition_key,
        d.name as definition_name,
        d.value_type as definition_value_type,
        dl.option_id,
        o.value as option_value,
        o.display_name as option_display_name,
        o.color as option_color,
        COUNT(DISTINCT dl.document_part_id) as option_count,
        (SELECT COUNT(DISTINCT dl2.document_part_id) 
         FROM ml_document_labels dl2 
         WHERE dl2.definition_id = dl.definition_id) as total_count
    FROM ml_document_labels dl
    JOIN ml_label_definitions d ON dl.definition_id = d.id
    JOIN ml_label_options o ON dl.option_id = o.id
    WHERE d.value_type IN ('select', 'multiselect') {definitions_filter}
    GROUP BY dl.definition_id, d.key, d.name, d.value_type, dl.option_id, o.value, o.display_name, o.color
    {order_by}
    """
    
    option_rows = fetch_all(option_query, params_base)
    for row in option_rows:
        result.append({
            'definition_id': row['definition_id'],
            'definition_key': row['definition_key'],
            'definition_name': row['definition_name'],
            'definition_value_type': row['definition_value_type'],
            'option_id': row['option_id'],
            'option_value': row['option_value'],
            'option_display_name': row['option_display_name'],
            'option_color': row['option_color'],
            'count': row['option_count'],
            'total': row['total_count'],
        })
    
    # Handle text type (group by text_value)
    text_query = f"""
    SELECT 
        dl.definition_id,
        d.key as definition_key,
        d.name as definition_name,
        d.value_type as definition_value_type,
        NULL as option_id,
        dl.text_value as option_value,
        dl.text_value as option_display_name,
        NULL as option_color,
        COUNT(DISTINCT dl.document_part_id) as option_count,
        (SELECT COUNT(DISTINCT dl2.document_part_id) 
         FROM ml_document_labels dl2 
         WHERE dl2.definition_id = dl.definition_id) as total_count
    FROM ml_document_labels dl
    JOIN ml_label_definitions d ON dl.definition_id = d.id
    WHERE d.value_type = 'text' AND dl.text_value IS NOT NULL {definitions_filter}
    GROUP BY dl.definition_id, d.key, d.name, d.value_type, dl.text_value
    {order_by}
    """
    
    text_rows = fetch_all(text_query, params_base)
    for row in text_rows:
        result.append({
            'definition_id': row['definition_id'],
            'definition_key': row['definition_key'],
            'definition_name': row['definition_name'],
            'definition_value_type': row['definition_value_type'],
            'option_id': row['option_id'],
            'option_value': row['option_value'],
            'option_display_name': row['option_display_name'],
            'option_color': row['option_color'],
            'count': row['option_count'],
            'total': row['total_count'],
        })
    
    # Handle number type (group by number_value)
    number_query = f"""
    SELECT 
        dl.definition_id,
        d.key as definition_key,
        d.name as definition_name,
        d.value_type as definition_value_type,
        NULL as option_id,
        CAST(dl.number_value AS TEXT) as option_value,
        CAST(dl.number_value AS TEXT) as option_display_name,
        NULL as option_color,
        COUNT(DISTINCT dl.document_part_id) as option_count,
        (SELECT COUNT(DISTINCT dl2.document_part_id) 
         FROM ml_document_labels dl2 
         WHERE dl2.definition_id = dl.definition_id) as total_count
    FROM ml_document_labels dl
    JOIN ml_label_definitions d ON dl.definition_id = d.id
    WHERE d.value_type = 'number' AND dl.number_value IS NOT NULL {definitions_filter}
    GROUP BY dl.definition_id, d.key, d.name, d.value_type, dl.number_value
    {order_by}
    """
    
    number_rows = fetch_all(number_query, params_base)
    for row in number_rows:
        result.append({
            'definition_id': row['definition_id'],
            'definition_key': row['definition_key'],
            'definition_name': row['definition_name'],
            'definition_value_type': row['definition_value_type'],
            'option_id': row['option_id'],
            'option_value': row['option_value'],
            'option_display_name': row['option_display_name'],
            'option_color': row['option_color'],
            'count': row['option_count'],
            'total': row['total_count'],
        })
    
    # Handle boolean type (group by bool_value)
    bool_query = f"""
    SELECT 
        dl.definition_id,
        d.key as definition_key,
        d.name as definition_name,
        d.value_type as definition_value_type,
        NULL as option_id,
        CASE WHEN dl.bool_value = 1 THEN 'true' ELSE 'false' END as option_value,
        CASE WHEN dl.bool_value = 1 THEN 'True' ELSE 'False' END as option_display_name,
        NULL as option_color,
        COUNT(DISTINCT dl.document_part_id) as option_count,
        (SELECT COUNT(DISTINCT dl2.document_part_id) 
         FROM ml_document_labels dl2 
         WHERE dl2.definition_id = dl.definition_id) as total_count
    FROM ml_document_labels dl
    JOIN ml_label_definitions d ON dl.definition_id = d.id
    WHERE d.value_type = 'boolean' AND dl.bool_value IS NOT NULL {definitions_filter}
    GROUP BY dl.definition_id, d.key, d.name, d.value_type, dl.bool_value
    {order_by}
    """
    
    bool_rows = fetch_all(bool_query, params_base)
    for row in bool_rows:
        result.append({
            'definition_id': row['definition_id'],
            'definition_key': row['definition_key'],
            'definition_name': row['definition_name'],
            'definition_value_type': row['definition_value_type'],
            'option_id': row['option_id'],
            'option_value': row['option_value'],
            'option_display_name': row['option_display_name'],
            'option_color': row['option_color'],
            'count': row['option_count'],
            'total': row['total_count'],
        })
    
    return result
