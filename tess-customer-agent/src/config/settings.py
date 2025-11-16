"""
TESS Configuration Management
Environment-based configuration using Pydantic Settings
"""
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_env: str = Field(default="dev", description="Environment: dev, uat, prod")
    app_host: str = Field(default="0.0.0.0", description="Application host")
    app_port: int = Field(default=8000, description="Application port")
    log_level: str = Field(default="INFO", description="Logging level")

    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model"
    )
    openai_temperature: float = Field(default=0.7, description="Model temperature")
    openai_max_tokens: int = Field(default=2000, description="Max tokens per response")

    # Frappe MCP (SEREBR)
    frappe_mcp_url: str = Field(
        default="http://localhost:3000/sse",
        description="Frappe MCP server URL"
    )
    frappe_api_key: Optional[str] = Field(default=None, description="Frappe API key")
    frappe_api_secret: Optional[str] = Field(default=None, description="Frappe API secret")
    mcp_timeout: int = Field(default=30000, description="MCP timeout in milliseconds")

    # PostgreSQL
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="tess_conversations", description="Database name")
    postgres_user: str = Field(default="tess_user", description="Database user")
    postgres_password: str = Field(..., description="Database password")
    postgres_pool_size: int = Field(default=10, description="Connection pool size")

    # ChromaDB
    chroma_persist_dir: str = Field(
        default="./data/chromadb",
        description="ChromaDB persistence directory"
    )
    chroma_collection_name: str = Field(
        default="knowledge_base",
        description="ChromaDB collection name"
    )
    chroma_top_k: int = Field(default=5, description="Number of results to retrieve")
    chroma_similarity_threshold: float = Field(
        default=0.7,
        description="Minimum similarity threshold"
    )

    # Agent Configuration
    max_conversation_history: int = Field(
        default=10,
        description="Max messages to keep in context"
    )
    conversation_summary_threshold: int = Field(
        default=15,
        description="Summarize when exceeding this many messages"
    )
    session_timeout_hours: int = Field(
        default=24,
        description="Session timeout in hours"
    )
    max_retries: int = Field(default=3, description="Max retry attempts for tools")
    retry_backoff_multiplier: int = Field(
        default=2,
        description="Exponential backoff multiplier"
    )

    model_config = SettingsConfigDict(
        env_file=None,  # We'll load this manually based on APP_ENV
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Validate app_env is one of the allowed values"""
        allowed = ["dev", "uat", "prod"]
        if v not in allowed:
            raise ValueError(f"app_env must be one of {allowed}, got {v}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log_level is valid"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got {v}")
        return v_upper

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL database URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.app_env == "dev"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.app_env == "prod"


def load_settings() -> Settings:
    """
    Load settings from environment-specific .env file

    Returns:
        Settings: Application settings
    """
    # Get environment from ENV variable or default to 'dev'
    app_env = os.getenv("APP_ENV", "dev")

    # Construct env file path
    env_file = f".env.{app_env}"

    # Check if env file exists
    if not os.path.exists(env_file):
        raise FileNotFoundError(
            f"Environment file '{env_file}' not found. "
            f"Please create it based on .env.example"
        )

    # Load settings from the env file
    from dotenv import load_dotenv
    load_dotenv(env_file, override=True)

    # Create and return settings instance
    return Settings()


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance (singleton pattern)

    Returns:
        Settings: Application settings
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
