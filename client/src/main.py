"""Durable Task client for the fan-out/fan-in average sample."""

import argparse
import json
import logging

from azure.identity import DefaultAzureCredential
from durabletask.azuremanaged.client import DurableTaskSchedulerClient

from settings import Settings

DEFAULT_ACTIVITY_COUNT = 10
logger = logging.getLogger(__name__)


def get_token_credential(settings: Settings) -> DefaultAzureCredential | None:
    """Create a managed identity credential when connecting to Azure."""
    if not settings.DTS_USE_MANAGED_IDENTITY:
        return None
    return DefaultAzureCredential(managed_identity_client_id=settings.AZURE_CLIENT_ID)


def positive_int(value: str) -> int:
    """Parse a positive integer CLI argument."""
    count = int(value)
    if count < 1:
        raise argparse.ArgumentTypeError("count must be at least 1")
    return count


def parse_args() -> argparse.Namespace:
    """Parse the number of activities to schedule."""
    parser = argparse.ArgumentParser(
        description="Run the calc_average Durable Task orchestration."
    )
    parser.add_argument(
        "count",
        nargs="?",
        default=DEFAULT_ACTIVITY_COUNT,
        type=positive_int,
        help=(
            "number of random-number activities to run "
            f"(default: {DEFAULT_ACTIVITY_COUNT})"
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Start an orchestration and display its completed result."""
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
            "calc_average", input=args.count
        )
        logger.info("Started calc_average instance: %s", instance_id)

        state = client.wait_for_orchestration_completion(instance_id)
        if state is None:
            raise RuntimeError(f"Orchestration instance {instance_id} was not found")
        state.raise_if_failed()

        logger.info(
            "Orchestration result: %s",
            json.dumps(state.get_output(), ensure_ascii=False),
        )
