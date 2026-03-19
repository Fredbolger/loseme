def run(conn):
    cur = conn.execute("PRAGMA table_info(document_parts);")
    columns = {row[1] for row in cur.fetchall()}

    if "chunker_name" not in columns:
        conn.execute("ALTER TABLE document_parts ADD COLUMN chunker_name TEXT;")
    if "chunker_version" not in columns:
        conn.execute("ALTER TABLE document_parts ADD COLUMN chunker_version TEXT;")
