"""Application settings for the Durable Task worker."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Connection settings for Durable Task Scheduler."""

    DTS_ENDPOINT: str = "localhost:8080"
    DTS_TASKHUB: str = "default"
    DTS_SECURE_CHANNEL: bool = False
    DTS_USE_MANAGED_IDENTITY: bool = False
    AZURE_CLIENT_ID: str | None = None
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4.1-mini"
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    AZURE_OPENAI_TIMEOUT_SECONDS: float = Field(default=60, gt=0)
    AZURE_STORAGE_ACCOUNT_URL: str
