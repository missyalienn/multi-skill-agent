from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel

from core.contracts import UseCaseConfig
from core.workflow import build_graph


# Minimal test scaffolding for exercising core/ directly -- not a use case,
# not maintained as part of use_cases/. Temporary until the messages migration
# (docs/plans/core-architecture-audit-plan.md, step 4) replaces `target`.
class MinimalResult(BaseModel):
    answer: str


def _search_prompt(target: str, refinement: str) -> str:
    return f"In one short sentence, answer: {target}"


def _extract_prompt(target: str, search_results: str, schema_json: str) -> str:
    return (
        f"The research below answers '{target}'. Extract just the one-word or "
        f"short-phrase answer, nothing else.\n\n"
        f"Research:\n{search_results}\n\n"
        f"Respond with ONLY valid JSON matching this schema, no preamble, no "
        f"markdown fences:\n{schema_json}"
    )


def _validate(instance: MinimalResult) -> tuple[bool, str]:
    return True, ""


config = UseCaseConfig(
    name="smoke_test",
    output_schema=MinimalResult,
    search_prompt=_search_prompt,
    extract_prompt=_extract_prompt,
    validate=_validate,
)

graph = build_graph(config)

result = graph.invoke({"target": "What is the capital of Argentina?"})
print(result)

print(graph.get_graph().draw_ascii())
