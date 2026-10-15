"""Run inside the existing client image for one private-network smoke test."""

import ipaddress
import json
import socket

from durabletask.azuremanaged.client import DurableTaskSchedulerClient

from main import get_token_credential
from settings import Settings


def main() -> None:
    # These hosts identify the dev environment being verified, not credentials.
    hosts = [
        "aoai-durabletask-dev-wyfvkj.openai.azure.com",
        "aoai-durabletask-dev-wyfvkj.services.ai.azure.com",
        "aoai-durabletask-dev-wyfvkj.cognitiveservices.azure.com",
        "stdurabletaskdevwyfvkj.blob.core.windows.net",
    ]
    expected = ipaddress.ip_network("10.0.1.0/24")
    for host in hosts:
        addresses = sorted(
            {entry[4][0] for entry in socket.getaddrinfo(host, 443, socket.AF_INET)}
        )
        print(json.dumps({"private_dns": host, "addresses": addresses}), flush=True)
        if not addresses or not all(
            ipaddress.ip_address(a) in expected for a in addresses
        ):
            raise RuntimeError(f"{host} did not resolve to the private endpoint subnet")

    settings = Settings()
    with DurableTaskSchedulerClient(
        host_address=settings.DTS_ENDPOINT,
        taskhub=settings.DTS_TASKHUB,
        token_credential=get_token_credential(settings),
        secure_channel=settings.DTS_SECURE_CHANNEL,
    ) as client:
        instance = client.schedule_new_orchestration(
            "analyze_reviews",
            input={
                "container": "input",
                "blob": "reviews-smoke.csv",
                "limit": 10,
                "parallelism": 2,
            },
        )
        print(json.dumps({"private_smoke_instance": instance}), flush=True)
        state = client.wait_for_orchestration_completion(instance, timeout=480)
        if state is None:
            raise RuntimeError("No orchestration state returned")
        print(
            json.dumps(
                {
                    "private_smoke_result": instance,
                    "status": state.runtime_status.name,
                    "output": state.serialized_output,
                }
            ),
            flush=True,
        )
        if state.runtime_status.name != "COMPLETED":
            raise RuntimeError("Private-network orchestration did not complete")
        report = json.loads(state.serialized_output or "{}")
        if report.get("succeeded") != 10 or report.get("failed") != 0:
            raise RuntimeError("Expected all ten reviews to succeed")


if __name__ == "__main__":
    main()
