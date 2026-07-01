"""
The engine. These three functions never change between use cases --
they're parameterized entirely by the UseCaseConfig passed in at build time.
"""

import json
import os

import anthropic
from langsmith.wrappers import wrap_anthropic

from core.contracts import UseCaseConfig, GraphState

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = wrap_anthropic(anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]))
    return _client


def make_search_node(config: UseCaseConfig):
    def search_node(state: GraphState) -> dict:
        client = get_client()
        prompt = config.search_prompt(state.target, state.search_query)

        response = client.messages.create(
            model=config.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "\n".join(b.text for b in response.content if b.type == "text").strip()

        return {"search_results": (state.search_results + "\n\n---\n\n" + text).strip()}

    return search_node


def make_extract_node(config: UseCaseConfig):
    def extract_node(state: GraphState) -> dict:
        client = get_client()
        schema_json = json.dumps(config.output_schema.model_json_schema(), indent=2)
        prompt = config.extract_prompt(state.target, state.search_results, schema_json)

        response = client.messages.create(
            model=config.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in response.content if b.type == "text").strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            instance = config.output_schema.model_validate_json(raw)
        except Exception:
            return {"result": None}

        return {"result": instance.model_dump()}

    return extract_node


def make_validate_node(config: UseCaseConfig):
    def validate_node(state: GraphState) -> dict:
        retry_count = state.retry_count

        if state.result is None:
            return {"done": False, "retry_count": retry_count + 1}

        instance = config.output_schema.model_validate(state.result)
        good_enough, gap = config.validate(instance)
        out_of_retries = retry_count >= state.max_retries

        if good_enough or out_of_retries:
            return {"done": True}

        return {
            "done": False,
            "retry_count": retry_count + 1,
            "search_query": gap,
        }

    return validate_node


def route_after_validate(state: GraphState) -> str:
    return "end" if state.done else "search"
