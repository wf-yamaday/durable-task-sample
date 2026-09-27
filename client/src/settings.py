"""Application settings for the Durable Task client."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Connection settings for Durable Task Scheduler."""

    DTS_ENDPOINT: str = "localhost:8080"
    DTS_TASKHUB: str = "default"
