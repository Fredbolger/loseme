def run(conn):
    cur = conn.execute("PRAGMA table_info(processed_documents);")
    columns = {row[1] for row in cur.fetchall()}

    # Already migrated → no-op
    if "content_type" in columns:
        return

    # Legacy schema → rename
    if "mime_type" in columns:
        conn.execute("""
            ALTER TABLE processed_documents
            RENAME COLUMN mime_type TO content_type
        """)
