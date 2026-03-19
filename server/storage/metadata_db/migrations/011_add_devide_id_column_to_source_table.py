def run(conn):
    cur = conn.execute("PRAGMA table_info(monitored_sources);")
    # Check if the device_id column already exists 
    columns = {row[1] for row in cur.fetchall()}
    if "device_id" not in columns:
        conn.execute("ALTER TABLE monitored_sources ADD COLUMN device_id TEXT;")

