def run(conn):
    cur = conn.execute("PRAGMA table_info(processed_documents);")
    columns = {row[1] for row in cur.fetchall()}

    # Already migrated → no-op
    if "extractor_name" in columns:
        return

    # Legacy schema → rename
    if "extractor" in columns:
        conn.execute("""
            ALTER TABLE processed_documents
            RENAME COLUMN extractor TO extractor_name;
        """)
