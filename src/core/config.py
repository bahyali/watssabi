from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.

    Loads configuration from environment variables and a .env file.
    """

    PROJECT_NAME: str = "Watssabi AI Collector"

    # PostgreSQL Database settings
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # Redis settings
    REDIS_HOST: str
    REDIS_PORT: int = 6379

    # Twilio settings
    TWILIO_AUTH_TOKEN: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_PHONE_NUMBER: str

    # OpenAI settings
    OPENAI_API_KEY: str

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        Constructs the SQLAlchemy database URI from individual components.
        The URI includes the '+psycopg' driver for compatibility with SQLAlchemy 2.0 and async operations.
        """
        dsn = PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )
        return str(dsn)

    # Configure Pydantic to load from a .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Create a single, importable instance of the settings
settings = Settings()
