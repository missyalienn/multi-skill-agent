"""
Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python main.py vendor_risk "Acme Corp"
    python main.py lead_enrichment "Acme Corp"
"""

import importlib
import json
import sys

from core.workflow import build_graph
from core.contracts import GraphState


def run(use_case_name: str, target: str) -> None:
    domain_module = importlib.import_module(f"use_cases.{use_case_name}")
    config = domain_module.config

    app = build_graph(config)
    initial_state = GraphState(target=target)

    print(f"[{config.name}] researching: {target}\n")

    final_state = None
    for step in app.stream(initial_state, stream_mode="values"):
        final_state = step
        if step.get("result") is not None:
            print(f"[pass {step.get('retry_count', 0)}] done={step.get('done', False)}")

    print("\n" + "=" * 60)
    print(json.dumps(final_state["result"], indent=2, default=str))
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python main.py <use_case> "Target"')
        print("Available use cases: vendor_risk, lead_enrichment")
        sys.exit(1)
    run(sys.argv[1], " ".join(sys.argv[2:]))

