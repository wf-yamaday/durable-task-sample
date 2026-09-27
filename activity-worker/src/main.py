"""Durable Task activity worker for the fan-out/fan-in average sample."""

import logging
import random
import signal
from threading import Event

from durabletask import task
from durabletask.azuremanaged.worker import DurableTaskSchedulerWorker

from settings import Settings

logger = logging.getLogger(__name__)


def generate_random_number(_: task.ActivityContext, _input: None) -> int:
    """Generate one random value for the fan-out operation."""
    return random.randint(1, 100)


def main() -> None:
    """Start the activity worker and wait for orchestration work."""
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
            worker.add_activity(generate_random_number)
            worker.use_work_item_filters()
            logger.info("Starting Durable Task activity worker")
            worker.start()

            shutdown_requested.wait()
            logger.info("Stopping Durable Task activity worker")
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
