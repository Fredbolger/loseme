from src.sources.base.registry import extractor_registry
from pathlib import Path

suffic_to_extractor = {
        ".pdf": {"unit_locator": "file://", "extractor_name": "pdf", "extractor_version": "0.1", "content_type": "application/pdf", },
        ".python": {"unit_locator": "file://", "extractor_name": "python", "extractor_version": "0.1", "content_type": "text/x-python", },
        ".txt": {"unit_locator": "file://", "extractor_name": "plaintext", "extractor_version": "0.1", "content_type": "text/plain", },
        ".md": {"unit_locator": "file://", "extractor_name": "plaintext", "extractor_version": "0.1", "content_type": "text/plain", },
        ".html": {"unit_locator": "file://", "extractor_name": "html", "extractor_version": "0.1", "content_type": "text/html", }
        }

def run(conn):
    # For all documents in processed_documents, if is_indexed == 1 get the source_instance_id
    cur = conn.execute("""
        SELECT run_id, source_instance_id, content_hash, unit_locator, content_type, extractor, extractor_version
        FROM processed_documents
        WHERE is_indexed = 1
    """)
    rows = cur.fetchall()

    # Now we need to check which runs where a "filesystem" source and remove those that where not
    for run_id, source_instance_id, content_hash, unit_locator, content_type, extractor, extractor_version in rows:
        # Get the run's source_type
        run_cur = conn.execute("""
            SELECT source_type
            FROM indexing_runs
            WHERE id = ?
        """, (run_id,))
        
        run_row = run_cur.fetchone()
        if run_row is None:
            continue
        if run_row[0] != "filesystem":
            continue

        # Get the file extension, which is stored in the documents tabel at "source_path" column
        # the source_instance_id is used to identify the document 

        source_path_cur = conn.execute("""
            SELECT source_path
            FROM documents
            WHERE source_instance_id = ?
        """, (source_instance_id,))
        source_path_row = source_path_cur.fetchone()

        if source_path_row is None:
            continue
        source_path = source_path_row[0]

        # Get the file extension
        file_extension = Path(source_path).suffix

        # Get the extractor info from the suffix_to_extractor mapping
        extractor_info = suffic_to_extractor.get(file_extension)

        if extractor_info is None:
            continue

        # Update the processed_documents table with the extractor info
        conn.execute("""
            UPDATE processed_documents
            SET 
                unit_locator = COALESCE(unit_locator, ?) ,
                content_type = COALESCE(content_type, ?),
                extractor = COALESCE(extractor, ?),
                extractor_version = COALESCE(extractor_version, ?)
            WHERE run_id = ? AND source_instance_id = ? AND content_hash = ?
        """, (
            extractor_info["unit_locator"] + source_path,
            extractor_info["content_type"],
            extractor_info["extractor_name"],
            extractor_info["extractor_version"],
            run_id,
            source_instance_id,
            content_hash
        ))
