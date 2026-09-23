#!/usr/bin/env bash
set -euo pipefail

# Reproduce the Hermes four-field extraction used in the RQ3 evaluation.
# The Hermes checkout is intentionally supplied by the caller because the
# upstream repository is maintained separately from this artifact repository.

EXPECTED_HERMES_COMMIT="d37fe752fec2592dcc10cc11fabfcb6429d6a216"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./reproduce_hermes.sh SPEC_FILE [OUTPUT_DIR]

Required environment variables:
  HERMES_DIR      Hermes/NEUTREX checkout at the pinned commit
  MODEL_REPO      Checkout containing neutrex/model_5g_nas and neutrex/saved_model
  HERMES_PYTHON   Python interpreter from the Hermes/NEUTREX environment

Optional:
  HERMES_NAME     Output name (default: basename of SPEC_FILE without suffix)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

SPEC_FILE="$1"
OUTPUT_DIR="${2:-${SCRIPT_DIR}/outputs/hermes}"
HERMES_DIR="${HERMES_DIR:-}"
MODEL_REPO="${MODEL_REPO:-}"
HERMES_PYTHON="${HERMES_PYTHON:-}"

for variable in HERMES_DIR MODEL_REPO HERMES_PYTHON; do
  if [[ -z "${!variable}" ]]; then
    echo "error: set ${variable} before running this script" >&2
    exit 2
  fi
done

[[ -f "$SPEC_FILE" ]] || { echo "error: specification file not found: $SPEC_FILE" >&2; exit 2; }
git -C "$HERMES_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "error: HERMES_DIR is not a Git checkout: $HERMES_DIR" >&2
  exit 2
}
[[ -x "$HERMES_PYTHON" ]] || { echo "error: HERMES_PYTHON is not executable: $HERMES_PYTHON" >&2; exit 2; }

actual_commit="$(git -C "$HERMES_DIR" rev-parse HEAD)"
if [[ "$actual_commit" != "$EXPECTED_HERMES_COMMIT" ]]; then
  echo "error: Hermes commit mismatch" >&2
  echo "  expected: $EXPECTED_HERMES_COMMIT" >&2
  echo "  actual:   $actual_commit" >&2
  exit 1
fi

name="${HERMES_NAME:-$(basename "$SPEC_FILE")}" 
name="${name%.*}"

exec "$HERMES_PYTHON" "$SCRIPT_DIR/hermes_4fields.py" \
  --raw-spec "$SPEC_FILE" \
  --name "$name" \
  --out-dir "$OUTPUT_DIR" \
  --hermes-repo "$HERMES_DIR" \
  --model-repo "$MODEL_REPO" \
  --python-bin "$HERMES_PYTHON"
