"""Durable Task worker for Amazon review analysis."""

import logging
import signal
from collections.abc import Generator
from datetime import timedelta
from threading import Event
from typing import Any

from azure.identity import DefaultAzureCredential
from durabletask import task
from durabletask.azuremanaged.worker import DurableTaskSchedulerWorker

from settings import Settings

logger = logging.getLogger(__name__)


def get_token_credential(settings: Settings) -> DefaultAzureCredential | None:
    """Create a managed identity credential when connecting to Azure."""
    if not settings.DTS_USE_MANAGED_IDENTITY:
        return None
    return DefaultAzureCredential(managed_identity_client_id=settings.AZURE_CLIENT_ID)


def analyze_reviews(
    context: task.OrchestrationContext, request: dict[str, Any]
) -> Generator[task.Task[Any], Any, dict[str, Any]]:
    """Analyze bounded batches, then persist results outside orchestration history."""
    limit = request["limit"]
    parallelism = request["parallelism"]
    if not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    if not isinstance(parallelism, int) or not 1 <= parallelism <= 1000:
        raise ValueError("parallelism must be between 1 and 1000")
    retry_policy = task.RetryPolicy(
        first_retry_interval=timedelta(seconds=5),
        max_number_of_attempts=3,
        backoff_coefficient=2,
    )
    reviews = yield context.call_activity(
        "load_reviews", input=request, retry_policy=retry_policy
    )
    results = []
    for start in range(0, len(reviews), parallelism):
        batch = yield task.when_all(
            [
                context.call_activity("analyze_review", input=review)
                for review in reviews[start : start + parallelism]
            ]
        )
        results.extend(batch)
    succeeded = [r for r in results if r["status"] == "succeeded"]
    metrics = {
        "total": len(results),
        "succeeded": len(succeeded),
        "failed": len(results) - len(succeeded),
        "average_score": (
            sum(r["predicted_score"] for r in succeeded) / len(succeeded)
            if succeeded
            else None
        ),
        "mae": (
            sum(abs(r["predicted_score"] - r["actual_score"]) for r in succeeded)
            / len(succeeded)
            if succeeded
            else None
        ),
    }
    output = yield context.call_activity(
        "save_results",
        retry_policy=retry_policy,
        input={
            "instance_id": context.instance_id,
            "report": {"metrics": metrics, "results": results},
        },
    )
    return output


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
            token_credential=get_token_credential(settings),
            secure_channel=settings.DTS_SECURE_CHANNEL,
        ) as worker:
            worker.add_orchestrator(analyze_reviews)
            worker.use_work_item_filters()
            logger.info("Starting Durable Task orchestrator worker")
            worker.start()

            shutdown_requested.wait()
            logger.info("Stopping Durable Task orchestrator worker")
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
