#!/bin/bash
#
# Project execution script.
#
# This script will:
# 1. Ensure the environment is set up by running install.sh.
# 2. Run the main application using uvicorn.
# 3. Pass any additional arguments to the uvicorn command.

set -euo pipefail

# --- Script Setup ---
# Get the directory of the currently executing script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

# --- Environment and Dependency Check ---
# Ensure dependencies are installed before running.
echo "INFO: Checking environment and dependencies..." >&2
bash "$SCRIPT_DIR/install.sh"

# --- Project Execution ---
# The manifest (pyproject.toml) shows this is a FastAPI project.
# The standard way to run it for development is with uvicorn.
# The application entry point is assumed to be 'app' in 'src/main.py'.
echo "INFO: Starting the application..." >&2
poetry run uvicorn src.main:app --reload "$@"