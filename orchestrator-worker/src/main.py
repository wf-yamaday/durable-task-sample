"""Durable Task worker for the fan-out/fan-in average sample."""

import logging
import signal
from collections.abc import Generator
from threading import Event
from typing import Any

from durabletask import task
from durabletask.azuremanaged.worker import DurableTaskSchedulerWorker

from settings import Settings

logger = logging.getLogger(__name__)
RANDOM_NUMBER_ACTIVITY = "generate_random_number"


def calc_average(
    context: task.OrchestrationContext, count: int
) -> Generator[task.Task[Any], Any, dict[str, Any]]:
    """Run random-number activities in parallel and return their average."""
    if count < 1:
        raise ValueError("count must be at least 1")

    numbers = yield task.when_all(
        [context.call_activity(RANDOM_NUMBER_ACTIVITY) for _ in range(count)]
    )
    return {"values": numbers, "average": sum(numbers) / len(numbers)}


def main() -> None:
    """Start the worker and wait for orchestration work."""
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    shutdown_requested = Event()

    def request_shutdown(signum: int, _frame: object) -> None:
        """Stop accepting work after a process termination signal."""
        logger.info(
            "Received %s; starting graceful shutdown", signal.Signals(signum).name
        )
        shutdown_requested.set()

    previous_handlers = {
        signal.SIGINT: signal.signal(signal.SIGINT, request_shutdown),
        signal.SIGTERM: signal.signal(signal.SIGTERM, request_shutdown),
    }

    try:
        with DurableTaskSchedulerWorker(
            host_address=settings.DTS_ENDPOINT,
            taskhub=settings.DTS_TASKHUB,
            token_credential=None,
            secure_channel=False,
        ) as worker:
            worker.add_orchestrator(calc_average)
            worker.use_work_item_filters()
            logger.info("Starting Durable Task orchestrator worker")
            worker.start()

            shutdown_requested.wait()
            logger.info("Stopping Durable Task orchestrator worker")
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
