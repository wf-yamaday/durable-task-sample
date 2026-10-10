"""Durable Task client for Amazon review analysis."""

import argparse
import logging

from azure.identity import DefaultAzureCredential
from durabletask.azuremanaged.client import DurableTaskSchedulerClient

from settings import Settings

DEFAULT_ACTIVITY_COUNT = 100
logger = logging.getLogger(__name__)


def get_token_credential(settings: Settings) -> DefaultAzureCredential | None:
    """Create a managed identity credential when connecting to Azure."""
    if not settings.DTS_USE_MANAGED_IDENTITY:
        return None
    return DefaultAzureCredential(managed_identity_client_id=settings.AZURE_CLIENT_ID)


def positive_int(value: str) -> int:
    """Parse a positive integer CLI argument."""
    count = int(value)
    if not 1 <= count <= 1000:
        raise argparse.ArgumentTypeError("value must be between 1 and 1000")
    return count


def parse_args() -> argparse.Namespace:
    """Parse the number of activities to schedule."""
    parser = argparse.ArgumentParser(
        description="Analyze Amazon food reviews from Blob Storage."
    )
    parser.add_argument(
        "count",
        nargs="?",
        default=DEFAULT_ACTIVITY_COUNT,
        type=positive_int,
        help=(f"maximum CSV rows to analyze (default: {DEFAULT_ACTIVITY_COUNT})"),
    )
    parser.add_argument("--container", help="input Blob container")
    parser.add_argument("--blob", help="input CSV Blob name")
    parser.add_argument("--parallelism", type=positive_int, default=5)
    return parser.parse_args()


def main() -> None:
    """Start an orchestration and exit without waiting for its completion."""
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    settings = Settings()

    with DurableTaskSchedulerClient(
        host_address=settings.DTS_ENDPOINT,
        taskhub=settings.DTS_TASKHUB,
        token_credential=get_token_credential(settings),
        secure_channel=settings.DTS_SECURE_CHANNEL,
    ) as client:
        instance_id = client.schedule_new_orchestration(
            "analyze_reviews",
            input={
                "container": args.container or settings.INPUT_CONTAINER,
                "blob": args.blob or settings.INPUT_BLOB,
                "limit": args.count,
                "parallelism": args.parallelism,
            },
        )
        logger.info("Started analyze_reviews instance: %s", instance_id)
