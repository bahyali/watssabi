# Stage 1: Builder
# This stage installs build tools and Python dependencies.
FROM python:3.11-slim as builder

# Set environment variables for Poetry
ENV POETRY_VERSION=1.8.2
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_NO_INTERACTION=1
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install dependencies needed for Poetry installation
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set working directory
WORKDIR /app

# Copy dependency definition files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to install dependencies to the system's site-packages
# and install only production dependencies.
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-dev


# Stage 2: Final Image
# This stage creates the final, lightweight production image.
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create a non-root user and group for security
RUN addgroup --system app && adduser --system --group app

# Copy installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the application source code and Alembic configuration
COPY src/ ./src
COPY alembic.ini .

# Set PYTHONPATH to make imports work correctly from the /app directory
ENV PYTHONPATH=/app

# Switch to the non-root user
USER app

# Expose the port the application will run on
EXPOSE 8000

# Command to run the application using Uvicorn
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
