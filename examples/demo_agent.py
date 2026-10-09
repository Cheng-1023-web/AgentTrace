import argparse
import random
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))
from agenttrace_sdk import AgentTraceClient


def run(question: str, should_fail: bool, base_url: str):
    client = AgentTraceClient(base_url)
    with client.start("Knowledge QA", "agent", input=question) as root:
        with client.start("Retrieve documents", "retrieval", input=question):
            time.sleep(0.02)
        with client.start("Call knowledge tool", "tool", input={"query": question}):
            time.sleep(0.015)
            if should_fail:
                raise RuntimeError("knowledge tool timed out after 250ms")
        with client.start("Generate answer", "model", input=question, model_name="simulated-local"):
            time.sleep(0.025)
            root.finish(output={"answer": f"Simulated answer for: {question}", "api_key": "sk-demo-secret"}, input_tokens=42, output_tokens=18, cost_usd=0.0008)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--runs", type=int, default=4)
    args = parser.parse_args()
    for i in range(args.runs):
        try:
            run(f"How does retrieval run {i + 1} work?", should_fail=i % 3 == 2, base_url=args.base_url)
        except RuntimeError:
            pass
        print(f"created demo run {i + 1}/{args.runs}")
    try:
        summary = httpx.get(f"{args.base_url.rstrip('/')}/api/v1/stats", timeout=3).json()
        print()
        print(f"demo complete: {summary['total_traces']} total traces | {summary['success_count']} success | {summary['failed_count']} failed")
        print(f"dashboard: http://localhost:5173/traces")
        print(f"api: {args.base_url.rstrip('/')}/api/v1/traces")
    except Exception as exc:
        print(f"demo data was sent, but summary is unavailable: {exc}")
