"""
The generic contract. Any business use case plugs into this loop by
providing a UseCaseConfig -- nothing in core/ changes between use cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Type

from pydantic import BaseModel


class GraphState(BaseModel):
    """Domain-agnostic state. `target` is whatever the agent is researching
    (a company name, a vendor, a lead, a job posting -- the config decides)."""

    target: str
    search_query: str = ""
    search_results: str = ""
    result: Optional[dict] = None  # validated against config.output_schema
    retry_count: int = 0
    max_retries: int = 2
    done: bool = False


@dataclass
class UseCaseConfig:
    """Everything that varies between use cases. This is the only file
    you write to adapt the framework to a new business problem."""

    name: str
    output_schema: Type[BaseModel]

    # Builds the search prompt for a given target + optional refinement query.
    search_prompt: Callable[[str, str], str]

    # Builds the extraction prompt: (target, search_results, schema_json) -> prompt.
    extract_prompt: Callable[[str, str, str], str]

    # Given a validated output instance, return (good_enough: bool, gap: str).
    # `gap` is only used when good_enough is False, to sharpen the retry query.
    validate: Callable[[BaseModel], tuple[bool, str]]

    model: str = "claude-sonnet-4-6"
