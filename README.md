# Watssabi AI Collector

A system to collect information from users via WhatsApp using an AI agent, built with FastAPI, PostgreSQL, and Redis.

## Technology Stack

| Category                | Technology                               |
| ----------------------- | ---------------------------------------- |
| **Backend Framework**   | FastAPI                                  |
| **Programming Language**| Python 3.11+                             |
| **Database (Primary)**  | PostgreSQL                               |
| **Database (Session)**  | Redis                                    |
| **Async Support**       | Uvicorn, SQLAlchemy 2.0 (async)          |
| **Dependency Management**| Poetry                                   |
| **Database Migrations** | Alembic                                  |
| **Containerization**    | Docker & Docker Compose                  |
| **Messaging API**       | Twilio                                   |
| **AI/LLM Provider**     | OpenAI                                   |

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Git:** To clone the repository.
- **Docker & Docker Compose:** To run the local development database and cache.
- **Poetry:** To manage Python dependencies. You can find installation instructions [here](https://python-poetry.org/docs/#installation).

## Local Development Setup

Follow these steps to get the application running on your local machine.

### 1. Clone the Repository

```bash
git clone https://github.com/bahyali/watssabi
cd watssabi
```

### 2. Configure Environment Variables

The application uses environment variables for configuration. Create a `.env` file by copying the example file.

```bash
cp .env.example .env
```

Now, open the `.env` file and fill in the required values. You will need to add your `OPENAI_API_KEY`. For local development using Docker Compose, the default database and Redis settings should work correctly.

```
# .env

# The name of the project, used in the API documentation.
PROJECT_NAME='Watssabi AI Collector'

# PostgreSQL Database settings
# The hostname 'db' matches the service name in docker-compose.yml
POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_DB=watssabi_db
POSTGRES_USER=watssabi_user
POSTGRES_PASSWORD=supersecretpassword

# Redis settings
# The hostname 'redis' matches the service name in docker-compose.yml
REDIS_HOST=redis
REDIS_PORT=6379

# Twilio settings
# Your Twilio Account SID from the Twilio Console
TWILIO_ACCOUNT_SID='your_account_sid_here'
# Your Twilio Auth Token from the Twilio Console
TWILIO_AUTH_TOKEN='your_auth_token_here'
# Your Twilio WhatsApp-enabled phone number (e.g., whatsapp:+14155238886)
TWILIO_PHONE_NUMBER='your_twilio_whatsapp_number_here'

# OpenAI settings
OPENAI_API_KEY='your_openai_api_key_here'
```

### 3. Install Dependencies

This project uses helper scripts in the `tools/` directory for common tasks. Run the install script to set up the Python environment.

```bash
./tools/install.sh
```

This script will use Poetry to create a virtual environment inside the project directory (`.venv/`) and install all required Python packages.

### 4. Start Services and Apply Migrations

First, start the PostgreSQL and Redis services using Docker Compose.

```bash
docker-compose up -d db redis
```

Once the containers are running, apply the database migrations (this runs Alembic inside the `app` container so all dependencies are available):

```bash
docker-compose run --rm app alembic upgrade head
```

Your local development environment is now fully set up.

## Running the Application

To run the FastAPI application, use the provided `run.sh` script.

```bash
./tools/run.sh
```

This will start the Uvicorn server with live-reloading enabled. The application will be available at `http://127.0.0.1:8000`.

You can check if the server is running by accessing the health check endpoint: `http://127.0.0.1:8000/health`.

## Testing Webhooks Locally with ngrok

To let external services (like Twilio) reach your locally running FastAPI app:

1. Set `NGROK_AUTHTOKEN` (and optionally `NGROK_REGION`) in `.env`. You can copy the placeholders from `.env.example`.
2. Start the ngrok tunnel alongside the app:

   ```bash
   docker-compose up ngrok
   ```

   This will expose the FastAPI service publicly and make the ngrok dashboard available at `http://127.0.0.1:4040`.

3. Copy the HTTPS forwarding URL shown in the ngrok dashboard and use it for your webhook configuration (e.g., Twilio WhatsApp webhook).

> Tip: You can customize tunnel options by editing `infra/ngrok/ngrok.yml` or override the region via the `NGROK_REGION` environment variable.

## Running Tests

To run the full test suite, use the `test.sh` script.

```bash
./tools/test.sh
```

This script automatically handles:
1.  Starting fresh, isolated PostgreSQL and Redis containers for the test run.
2.  Running all tests using `pytest`.
3.  Shutting down and cleaning up the test containers after the tests complete.

## Production Deployment

Whether you deploy on bare metal, Kubernetes, or the provided AWS Terraform stack, the production flow follows the same core steps:

1. **Build the image:** `docker build -t watssabi-ai-collector:latest .`
2. **Provide environment variables:** copy `.env` to your secret manager or pass the values directly as container env vars (OpenAI, Twilio, Postgres, Redis, project name, etc.). Never bake secrets into the image.
3. **Apply database migrations:** run `alembic upgrade head` using the same image and configuration that will power the API (e.g., `docker run --rm --env-file prod.env watssabi-ai-collector alembic upgrade head`).
4. **Run the app container:** start Uvicorn via the packaged `tools/run.sh` or your own process manager, exposing port 8000 behind your reverse proxy / load balancer.
5. **Monitor & log:** structured JSON logs are already emitted via `structlog`, so point stdout to your logging stack (CloudWatch, ELK, etc.).
6. **Scale in AWS:** the `infra/terraform` directory provisions ECS Fargate, RDS, and ElastiCache; set the required variables, run `terraform apply`, then push the built image to the generated ECR repository.

## Available Scripts

The `tools/` directory contains scripts for common development tasks:

| Script          | Description                                                              |
| --------------- | ------------------------------------------------------------------------ |
| `install.sh`    | Installs all Python dependencies using Poetry into a local `.venv`.      |
| `run.sh`        | Runs the FastAPI application in development mode with live-reloading.    |
| `test.sh`       | Runs the complete test suite, managing test-specific Docker containers.  |
| `lint.sh`       | Runs `pylint` on the source code to check for errors and warnings.       |
