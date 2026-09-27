"""Application settings for the Durable Task worker."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Connection settings for Durable Task Scheduler."""

    DTS_ENDPOINT: str = "localhost:8080"
    DTS_TASKHUB: str = "default"
    DTS_SECURE_CHANNEL: bool = False
    DTS_USE_MANAGED_IDENTITY: bool = False
    AZURE_CLIENT_ID: str | None = None
