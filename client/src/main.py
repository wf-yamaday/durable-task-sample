"""Durable Task client for the fan-out/fan-in average sample."""

import argparse
import json
import os

from durabletask.azuremanaged.client import DurableTaskSchedulerClient

TASKHUB = "default"
EMULATOR_ENDPOINT = "localhost:8080"
DEFAULT_ACTIVITY_COUNT = 10


def positive_int(value: str) -> int:
    """Parse a positive integer CLI argument."""
    count = int(value)
    if count < 1:
        raise argparse.ArgumentTypeError("count must be at least 1")
    return count


def parse_args() -> argparse.Namespace:
    """Parse the number of activities to schedule."""
    parser = argparse.ArgumentParser(
        description="Run the fan_out_average Durable Task orchestration."
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
    args = parse_args()

    with DurableTaskSchedulerClient(
        host_address=os.getenv("DTS_ENDPOINT", EMULATOR_ENDPOINT),
        taskhub=os.getenv("DTS_TASKHUB", TASKHUB),
        token_credential=None,
        secure_channel=False,
    ) as client:
        instance_id = client.schedule_new_orchestration(
            "fan_out_average", input=args.count
        )
        print(f"Started fan_out_average instance: {instance_id}")

        state = client.wait_for_orchestration_completion(instance_id)
        if state is None:
            raise RuntimeError(f"Orchestration instance {instance_id} was not found")
        state.raise_if_failed()

        print(json.dumps(state.get_output(), ensure_ascii=False))
