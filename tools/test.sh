#!/bin/bash
#
# Project test execution script.
#
# This script will:
# 1. Ensure the environment is set up by running install.sh.
# 2. Start required services (PostgreSQL, Redis) using Docker Compose.
# 3. Run the project's tests using pytest.
# 4. Shut down the services upon completion.
# 5. Pass any additional arguments to the pytest command.

set -euo pipefail

# --- Script Setup ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

# --- Set Test Environment Variables ---
# These are needed by docker-compose to configure the services.
# They should match the values used by the tests in `tests/conftest.py`.
export POSTGRES_DB="test_db"
export POSTGRES_USER="test_user"
export POSTGRES_PASSWORD="test_password"

# --- Cleanup Function ---
cleanup() {
  echo "INFO: Shutting down test environment..." >&2
  docker-compose down -v --remove-orphans
}

# Trap EXIT signal to ensure cleanup runs, whether tests pass or fail.
trap cleanup EXIT

# --- Environment and Dependency Check ---
echo "INFO: Checking environment and dependencies..." >&2
bash "$SCRIPT_DIR/install.sh"

# Ensure pytest is installed as a dev dependency.
if ! poetry run pytest --version >/dev/null 2>&1; then
  echo "INFO: pytest not found. Installing..." >&2
  poetry add pytest --group dev >&2
fi

# --- Start Test Environment ---
echo "INFO: Starting test environment with Docker Compose..." >&2
# Start only the database and redis services required for testing.
# Use --force-recreate to ensure a clean state for each test run.
docker-compose up -d --force-recreate db redis

# A short wait to ensure services are fully ready to accept connections,
# even though healthchecks are in place.
echo "INFO: Waiting for services to initialize..." >&2
sleep 5

# --- Test Execution ---
echo "INFO: Running tests..." >&2
# The `poetry run` command executes within the project's virtual environment.
poetry run pytest "$@"