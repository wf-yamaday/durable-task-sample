"""Offline checks for CSV parsing, safe model input, and result storage."""

import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openai import OpenAIError
from pydantic import ValidationError

from reviews import ReviewActivities, ReviewAnalysis, csv_lines, parse_reviews
from settings import Settings


class ReviewTests(unittest.TestCase):
    def test_multiline_csv_and_chunked_utf8(self):
        data = '\ufeffId,Text,Score\r\n1,"良い味,です\nおすすめ",5\r\n2,Okay,3\r\n'
        encoded = data.encode("utf-8")
        chunks = [encoded[i : i + 2] for i in range(0, len(encoded), 2)]
        rows = parse_reviews(csv_lines(chunks), 1)
        self.assertEqual(
            rows,
            [{"review_id": "1", "text": "良い味,です\nおすすめ", "actual_score": 5}],
        )

    def test_invalid_csv(self):
        for data in [
            "Text\nHello\n",
            "Id,Text,Score\n1,,3\n",
            "Id,Text,Score\n1,Hello,6\n",
        ]:
            with self.assertRaises(ValueError):
                parse_reviews(io.StringIO(data), 100)
        with self.assertRaises(ValueError):
            parse_reviews(io.StringIO("Id,Text,Score\n"), 1001)

    def test_validated_rating(self):
        with self.assertRaises(ValidationError):
            ReviewAnalysis(predicted_score=6, summary="summary", reason="reason")

    def activities(self):
        activities = ReviewActivities.__new__(ReviewActivities)
        activities.llm = MagicMock()
        activities.blobs = MagicMock()
        activities.deployment = "test"
        activities.reasoning_effort = "none"
        activities.max_completion_tokens = 1024
        return activities

    def test_v1_client_and_default_model(self):
        settings = Settings(
            AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/",
            AZURE_STORAGE_ACCOUNT_URL="https://example.blob.core.windows.net/",
        )
        credential = MagicMock()
        with (
            patch("reviews.OpenAI") as client,
            patch("reviews.BlobServiceClient"),
            patch("reviews.get_bearer_token_provider") as provider,
        ):
            activities = ReviewActivities(settings, credential)
        self.assertEqual(activities.deployment, "gpt-5.6-luna")
        self.assertEqual(
            client.call_args.kwargs["base_url"],
            "https://example.openai.azure.com/openai/v1/",
        )
        self.assertIs(client.call_args.kwargs["api_key"], provider.return_value)
        provider.assert_called_once_with(credential, "https://ai.azure.com/.default")

    def test_only_text_is_sent_to_model(self):
        activities = self.activities()
        activities.llm.chat.completions.parse.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        parsed=ReviewAnalysis(
                            predicted_score=4, summary="要約", reason="理由"
                        )
                    )
                )
            ]
        )
        result = activities.analyze_review(
            None, {"review_id": "1", "text": "Tasty", "actual_score": 5}
        )
        messages = activities.llm.chat.completions.parse.call_args.kwargs["messages"]
        self.assertEqual(messages[1], {"role": "user", "content": "Tasty"})
        self.assertEqual(result["predicted_score"], 4)
        self.assertEqual(result["status"], "succeeded")
        options = activities.llm.chat.completions.parse.call_args.kwargs
        self.assertEqual(options["reasoning_effort"], "none")
        self.assertEqual(options["max_completion_tokens"], 1024)

    def test_api_failure_does_not_expose_error_body(self):
        activities = self.activities()
        activities.llm.chat.completions.parse.side_effect = OpenAIError("secret")
        result = activities.analyze_review(
            None, {"review_id": "1", "text": "Tasty", "actual_score": 5}
        )
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("secret", json.dumps(result))

    def test_result_upload_is_idempotent(self):
        activities = self.activities()
        result = activities.save_results(
            None, {"instance_id": "instance", "report": {"metrics": {"total": 1}}}
        )
        self.assertEqual(result["blob"], "instance/results.json")
        activities.blobs.get_blob_client.assert_called_once_with(
            "results", "instance/results.json"
        )
        self.assertTrue(
            activities.blobs.get_blob_client().upload_blob.call_args.kwargs["overwrite"]
        )
