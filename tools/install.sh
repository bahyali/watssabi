#!/bin/bash
#
# Environment setup and dependency installation script.
# This script is idempotent.
#
# This script will:
# 1. Check for the presence of 'poetry'.
# 2. Configure poetry to create the virtual environment inside the project (.venv).
# 3. Install/update all dependencies from pyproject.toml.

set -euo pipefail

# --- Script Setup ---
# Find the project root, assuming this script is in 'project_root/tools/'.
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"

# --- Sanity Checks ---
if ! command -v poetry &> /dev/null; then
    echo "Error: poetry is not installed or not in your PATH." >&2
    echo "Please install poetry by following the instructions at https://python-poetry.org/docs/#installation" >&2
    exit 1
fi

# --- Environment and Dependency Management ---
echo "INFO: Ensuring virtual environment exists and is up-to-date..." >&2

# Configure poetry to create the virtualenv in the project's root directory
# This makes the environment location predictable for other tools and scripts.
poetry config virtualenvs.in-project true >/dev/null 2>&1

# Install dependencies. This is idempotent.
# It will create the .venv if it doesn't exist and install/update dependencies.
# The output is sent to stderr to not interfere with scripts that might capture stdout.
poetry lock && poetry install --no-interaction --no-ansi >&2

echo "INFO: Environment setup complete. Dependencies are installed in '$PROJECT_ROOT/.venv'" >&2