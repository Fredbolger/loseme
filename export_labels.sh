#!/usr/bin/env bash

set -euo pipefail

CONTAINER="${1:-}"
OUTPUT="${2:-labels_export.csv}"

if [[ -z "$CONTAINER" ]]; then
    echo "Usage: $0 <container-name> [output.csv]"
    exit 1
fi

# Check that python3 exists
if ! docker exec "$CONTAINER" python3 --version >/dev/null 2>&1; then
    echo "Error: python3 not found in container '$CONTAINER'."
    exit 1
fi

docker exec -i "$CONTAINER" python3 - <<'PY' >"$OUTPUT"
import sqlite3
import csv
import sys

DB = "/var/lib/loseme/metadata/metadata.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
SELECT
  dl.document_part_id,
  dp.source_path,
  dp.source_type,
  ld.key,
  ld.name,
  lo.value,
  dl.text_value,
  dl.number_value,
  dl.bool_value,
  dl.confidence,
  dl.label_source,
  dl.created_at
FROM ml_document_labels dl
JOIN ml_label_definitions ld
  ON ld.id = dl.definition_id
LEFT JOIN ml_label_options lo
  ON lo.id = dl.option_id
LEFT JOIN document_parts dp
  ON dp.document_part_id = dl.document_part_id
ORDER BY dl.created_at;
""")

writer = csv.writer(sys.stdout)
writer.writerow([col[0] for col in cur.description])
writer.writerows(cur.fetchall())

conn.close()
PY

echo "Exported labels to '$OUTPUT'"
