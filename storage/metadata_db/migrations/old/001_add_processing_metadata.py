def run(conn):
    def has(col):
        cur = conn.execute("PRAGMA table_info(processed_documents);")
        return any(row[1] == col for row in cur.fetchall())

    if not has("unit_locator"):
        conn.execute("ALTER TABLE processed_documents ADD COLUMN unit_locator TEXT;")

    if not has("mime_type"):
        conn.execute("ALTER TABLE processed_documents ADD COLUMN mime_type TEXT;")

    if not has("extractor"):
        conn.execute("ALTER TABLE processed_documents ADD COLUMN extractor TEXT;")

    if not has("extractor_version"):
        conn.execute("ALTER TABLE processed_documents ADD COLUMN extractor_version TEXT;")

