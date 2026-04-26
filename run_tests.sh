#!/usr/bin/env bash
# run_tests.sh — called by Drone CI; always executes from the repo root.
#
# Usage:
#   ./run_tests.sh              # all tests
#   ./run_tests.sh unit         # unit tests only
#   ./run_tests.sh integration  # integration tests only
#   ./run_tests.sh coverage     # all tests + coverage report

set -euo pipefail

# ── Resolve repo root regardless of where the script is called from ──────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $(pwd)"
echo "Python: $(python --version)"

# ── Environment defaults (Drone sets these; locals use fallbacks) ─────────
export PYTHONPATH="${PYTHONPATH:-server:client:core}"
export LOSEME_HOST_ROOT="${LOSEME_HOST_ROOT:-/host/data}"
export LOSEME_CONTAINER_ROOT="${LOSEME_CONTAINER_ROOT:-/mnt/data}"
export LOSEME_DEVICE_ID="${LOSEME_DEVICE_ID:-ci-runner}"
export LOSEME_EMBEDDING_MODEL="${LOSEME_EMBEDDING_MODEL:-sentence-transformer:all-MiniLM-L6-v2}"
export LOSEME_CHUNKER="${LOSEME_CHUNKER:-simple}"
export LOSEME_VECTOR_STORAGE="${LOSEME_VECTOR_STORAGE:-in-memory}"
export QDRANT_URL="${QDRANT_URL:-http://localhost:9999}"

# ── Test selection ────────────────────────────────────────────────────────
MODE="${1:-all}"

UNIT_FILES="
  tests/test_ids.py
  tests/test_chunkers.py
  tests/test_vector_store.py
  tests/test_embeddings.py
  tests/test_extractors.py
  tests/test_metadata_db.py
  tests/test_document_models.py
  tests/test_scope_models.py
  tests/test_cache.py
  tests/test_docker_path_translation.py
"

INTEGRATION_FILES="
  tests/test_api_integration.py
  tests/test_ingest_skip_logic.py
  tests/test_preview.py
"

case "$MODE" in
  unit)
    echo "=== Running unit tests ==="
    # shellcheck disable=SC2086
    python -m pytest $UNIT_FILES -v --tb=short -x
    ;;
  integration)
    echo "=== Running integration tests ==="
    # shellcheck disable=SC2086
    python -m pytest $INTEGRATION_FILES -v --tb=short -x
    ;;
  coverage)
    echo "=== Running all tests with coverage ==="
    python -m pytest tests/ \
      --cov=server \
      --cov=client \
      --cov=core \
      --cov-report=term-missing \
      --cov-report=xml:coverage.xml \
      -v --tb=short
    ;;
  all | *)
    echo "=== Running unit tests ==="
    # shellcheck disable=SC2086
    python -m pytest $UNIT_FILES -v --tb=short -x
    echo ""
    echo "=== Running integration tests ==="
    # shellcheck disable=SC2086
    python -m pytest $INTEGRATION_FILES -v --tb=short -x
    ;;
esac
