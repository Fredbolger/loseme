"""
Migration 013: Generic ML label engine.

Three tables:
  ml_label_definitions — the *schema* of a label dimension (one row per
                          dimension, e.g. "sentiment", "urgency", "topic")
  ml_label_options     — allowed values for select/multiselect definitions
  ml_document_labels   — the actual assignment: document_part_id -> value

To add a brand-new label dimension, insert a row into
ml_label_definitions (+ ml_label_options if it's a select type) via the
API/UI. No schema change, no migration, no route change required.
"""


def run(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ml_label_definitions (
            id           TEXT PRIMARY KEY,
            key          TEXT NOT NULL UNIQUE,   -- machine slug, e.g. "sentiment"
            name         TEXT NOT NULL,          -- display name, e.g. "Sentiment"
            description  TEXT,
            value_type   TEXT NOT NULL CHECK(value_type IN
                             ('select','multiselect','text','boolean','number')),
            color        TEXT,                   -- default swatch for this dimension
            is_active    INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ml_label_options (
            id             TEXT PRIMARY KEY,
            definition_id  TEXT NOT NULL REFERENCES ml_label_definitions(id) ON DELETE CASCADE,
            value          TEXT NOT NULL,         -- machine value, e.g. "positive"
            display_name   TEXT NOT NULL,         -- "Positive"
            color          TEXT,
            sort_order     INTEGER NOT NULL DEFAULT 0,
            UNIQUE(definition_id, value)
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ml_document_labels (
            id                TEXT PRIMARY KEY,
            document_part_id  TEXT NOT NULL REFERENCES document_parts(document_part_id) ON DELETE CASCADE,
            definition_id     TEXT NOT NULL REFERENCES ml_label_definitions(id) ON DELETE CASCADE,
            option_id         TEXT REFERENCES ml_label_options(id) ON DELETE CASCADE,
            text_value        TEXT,     -- used when value_type = 'text'
            number_value      REAL,     -- used when value_type = 'number'
            bool_value        INTEGER,  -- used when value_type = 'boolean'
            confidence        REAL,     -- NULL = human label; 0..1 = model prediction
            label_source      TEXT NOT NULL DEFAULT 'human' CHECK(label_source IN ('human','model')),
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ml_document_labels_doc ON ml_document_labels(document_part_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ml_document_labels_def ON ml_document_labels(definition_id);")
    conn.commit()
