"""Offline generator tests for bounded fan-out and aggregate metrics."""

import unittest
from unittest.mock import MagicMock, patch

from main import analyze_reviews


class OrchestrationTests(unittest.TestCase):
    def run_workflow(self, results):
        context = MagicMock(instance_id="instance")
        request = {
            "container": "input",
            "blob": "Reviews.csv",
            "limit": 100,
            "parallelism": 2,
        }
        workflow = analyze_reviews(context, request)
        next(workflow)
        rows = [{"review_id": str(i)} for i in range(len(results))]
        with patch("main.task.when_all", side_effect=lambda tasks: tasks):
            if rows:
                workflow.send(rows)
                for start in range(0, len(results), 2):
                    workflow.send(results[start : start + 2])
            else:
                workflow.send([])
        save = context.call_activity.call_args
        self.assertEqual(save.args[0], "save_results")
        self.assertEqual(save.kwargs["input"]["instance_id"], "instance")
        with self.assertRaises(StopIteration) as done:
            workflow.send({"blob": "instance/results.json"})
        self.assertEqual(done.exception.value, {"blob": "instance/results.json"})
        return save.kwargs["input"]["report"]["metrics"], context

    def test_batches_and_partial_failures(self):
        metrics, context = self.run_workflow(
            [
                {"status": "succeeded", "predicted_score": 4, "actual_score": 5},
                {"status": "failed"},
                {"status": "succeeded", "predicted_score": 2, "actual_score": 2},
            ]
        )
        self.assertEqual(
            metrics,
            {"total": 3, "succeeded": 2, "failed": 1, "average_score": 3, "mae": 0.5},
        )
        self.assertEqual(context.call_activity.call_count, 5)

    def test_empty_and_all_failed(self):
        for results in [[], [{"status": "failed"}]]:
            metrics, _ = self.run_workflow(results)
            self.assertIsNone(metrics["mae"])
            self.assertIsNone(metrics["average_score"])

    def test_invalid_limits(self):
        for limit, parallelism in [(0, 5), (1001, 5), (100, 0)]:
            with self.assertRaises(ValueError):
                next(
                    analyze_reviews(
                        MagicMock(), {"limit": limit, "parallelism": parallelism}
                    )
                )
