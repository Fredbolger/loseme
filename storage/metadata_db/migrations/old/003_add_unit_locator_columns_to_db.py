def run(conn):
    cur = conn.execute("PRAGMA table_info(processed_documents);")
    columns = {row[1] for row in cur.fetchall()}

    if "unit_locator" not in columns:
        conn.execute("""
            ALTER TABLE processed_documents
            ADD COLUMN unit_locator TEXT
        """)

    if "extractor" not in columns:
        conn.execute("""
            ALTER TABLE processed_documents
            ADD COLUMN extractor TEXT
        """)

    if "extractor_version" not in columns:
        conn.execute("""
            ALTER TABLE processed_documents
            ADD COLUMN extractor_version TEXT
        """)
