#!/bin/bash
#
# Project linting script.
#
# This script will:
# 1. Ensure the environment is set up by running install.sh.
# 2. Ensure pylint is installed.
# 3. Lint the source code using pylint, focusing on errors and critical warnings.
# 4. Output results exclusively in the specified JSON format to stdout.
# 5. Exit with 0 on success (no issues found), non-zero on failure.

set -euo pipefail

# --- Script Setup ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

# --- Environment and Dependency Check ---
# Run install script silently, directing all its output to stderr.
bash "$SCRIPT_DIR/install.sh" >&2

# Ensure pylint is installed as a dev dependency.
if ! poetry run pylint --version >/dev/null 2>&1; then
  echo "INFO: pylint not found. Installing..." >&2
  poetry add pylint --group dev >&2
fi

# Ensure jq is installed for JSON transformation.
if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Please install it to format the linting output." >&2
    exit 1
fi

# --- Linting Execution ---
# Run pylint, capturing its JSON output.
# We use '|| true' to prevent 'set -e' from exiting if pylint finds issues,
# which allows us to process the output regardless.
# We only enable warnings (W), errors (E), and fatal errors (F) as requested.
LINT_TARGETS="src tests"
echo "INFO: Running pylint on '$LINT_TARGETS'..." >&2
LINT_OUTPUT=$(poetry run pylint --disable=all --enable=W,E,F --output-format=json $LINT_TARGETS || true)

# If pylint output is empty or an empty JSON array, no issues were found.
if [[ -z "$LINT_OUTPUT" || "$LINT_OUTPUT" == "[]" ]]; then
  echo "[]"
  exit 0
fi

# Transform the pylint JSON to the required format using jq.
# This transformed output is the only thing printed to stdout.
echo "$LINT_OUTPUT" | jq '[.[] | {type: .symbol, path: .path, obj: .obj, message: .message, line: .line, column: .column}]'

# If we reached this point, it means linting issues were found.
exit 1