"""Durable Task activity worker for Amazon review analysis."""

import logging
import signal
from threading import Event

from azure.identity import DefaultAzureCredential
from durabletask.azuremanaged.worker import DurableTaskSchedulerWorker

from reviews import ReviewActivities
from settings import Settings

logger = logging.getLogger(__name__)


def get_token_credential(settings: Settings) -> DefaultAzureCredential | None:
    """Create a managed identity credential when connecting to Azure."""
    if not settings.DTS_USE_MANAGED_IDENTITY:
        return None
    return DefaultAzureCredential(managed_identity_client_id=settings.AZURE_CLIENT_ID)


def main() -> None:
    """Start the activity worker and wait for orchestration work."""
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    credential = DefaultAzureCredential(
        managed_identity_client_id=settings.AZURE_CLIENT_ID
    )
    activities = ReviewActivities(settings, credential)
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
            token_credential=get_token_credential(settings),
            secure_channel=settings.DTS_SECURE_CHANNEL,
        ) as worker:
            worker.add_activity(activities.load_reviews)
            worker.add_activity(activities.analyze_review)
            worker.add_activity(activities.save_results)
            worker.use_work_item_filters()
            logger.info("Starting Durable Task activity worker")
            worker.start()

            shutdown_requested.wait()
            logger.info("Stopping Durable Task activity worker")
    finally:
        activities.close()
        credential.close()
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
