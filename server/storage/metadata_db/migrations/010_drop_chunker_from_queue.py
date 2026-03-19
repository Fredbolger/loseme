def run(conn):
    cur = conn.execute("PRAGMA table_info(document_parts_queue);")
    columns = {row[1] for row in cur.fetchall()}
    if "chunker_name" in columns:
        conn.execute("ALTER TABLE document_parts_queue DROP COLUMN chunker_name;")
    if "chunker_version" in columns:
        conn.execute("ALTER TABLE document_parts_queue DROP COLUMN chunker_version;")
