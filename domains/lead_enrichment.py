"""
A completely different business use case (sales lead enrichment instead of
vendor risk), built with zero changes to core/. This is the proof that the
abstraction actually holds.
"""

from typing import Optional

from pydantic import BaseModel, Field

from core.contracts import DomainConfig


class LeadProfile(BaseModel):
    company_name: str
    industry: Optional[str] = None
    estimated_size: Optional[str] = None
    recent_signals: list[str] = Field(
        default_factory=list, description="Funding, hiring, product launches, etc."
    )
    icp_fit_notes: str
    confidence: float = Field(ge=0.0, le=1.0)
    missing_information: list[str] = Field(default_factory=list)


def _search_prompt(target: str, refinement: str) -> str:
    base = (
        f"Search for recent information about '{target}' useful for sales outreach: "
        f"industry, company size, funding, recent hiring, product launches, news."
    )
    if refinement:
        base += f" Specifically focus on: {refinement}"
    return base


def _extract_prompt(target: str, search_results: str, schema_json: str) -> str:
    return (
        f"Based ONLY on the research below, produce a lead profile for '{target}'.\n\n"
        f"Research:\n{search_results}\n\n"
        f"Respond with ONLY valid JSON matching this schema, no preamble, no markdown "
        f"fences:\n{schema_json}\n\n"
        f"Be honest in missing_information rather than guessing."
    )


def _validate(profile: LeadProfile) -> tuple[bool, str]:
    good_enough = profile.confidence >= 0.6 and len(profile.missing_information) <= 1
    gap = "; ".join(profile.missing_information) or "general additional detail"
    return good_enough, gap


config = DomainConfig(
    name="lead_enrichment",
    output_schema=LeadProfile,
    search_prompt=_search_prompt,
    extract_prompt=_extract_prompt,
    validate=_validate,
)
