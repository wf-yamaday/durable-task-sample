"""Durable Task worker for the fan-out/fan-in average sample."""

import logging
import os
import random
from collections.abc import Generator
from threading import Event
from typing import Any

from durabletask import task
from durabletask.azuremanaged.worker import DurableTaskSchedulerWorker

TASKHUB = "default"
EMULATOR_ENDPOINT = "localhost:8080"
logger = logging.getLogger(__name__)


def generate_random_number(_: task.ActivityContext, _input: None) -> int:
    """Generate one random value for the fan-out operation."""
    return random.randint(1, 100)


def fan_out_average(
    context: task.OrchestrationContext, count: int
) -> Generator[task.Task[Any], Any, dict[str, Any]]:
    """Run random-number activities in parallel and return their average."""
    if count < 1:
        raise ValueError("count must be at least 1")

    numbers = yield task.when_all(
        [context.call_activity(generate_random_number) for _ in range(count)]
    )
    return {"values": numbers, "average": sum(numbers) / len(numbers)}


def main() -> None:
    """Start the worker and wait for orchestration work."""
    logging.basicConfig(level=logging.INFO)

    with DurableTaskSchedulerWorker(
        host_address=os.getenv("DTS_ENDPOINT", EMULATOR_ENDPOINT),
        taskhub=os.getenv("DTS_TASKHUB", TASKHUB),
        token_credential=None,
        secure_channel=False,
    ) as worker:
        worker.add_orchestrator(fan_out_average)
        worker.add_activity(generate_random_number)
        logger.info("Starting Durable Task worker")
        worker.start()

        try:
            Event().wait()
        except KeyboardInterrupt:
            logger.info("Stopping Durable Task worker")
