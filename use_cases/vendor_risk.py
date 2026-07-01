from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from core.contracts import UseCaseConfig


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskFlag(BaseModel):
    category: str
    description: str
    severity: RiskSeverity
    source_note: Optional[str] = None


class VendorRiskProfile(BaseModel):
    company_name: str
    summary: str
    financial_health: str
    flags: list[RiskFlag] = Field(default_factory=list)
    overall_severity: RiskSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    missing_information: list[str] = Field(default_factory=list)


def _search_prompt(target: str, refinement: str) -> str:
    base = (
        f"Search for recent, factual information about '{target}' relevant to vendor "
        f"risk assessment: financial stability, funding/layoffs, litigation, regulatory "
        f"actions, security incidents, leadership/ownership changes."
    )
    if refinement:
        base += f" Specifically focus on: {refinement}"
    return base


def _extract_prompt(target: str, search_results: str, schema_json: str) -> str:
    return (
        f"Based ONLY on the research below, produce a vendor risk profile for '{target}'.\n\n"
        f"Research:\n{search_results}\n\n"
        f"Respond with ONLY valid JSON matching this schema, no preamble, no markdown "
        f"fences:\n{schema_json}\n\n"
        f"If research is thin on a field, say so in missing_information rather than "
        f"guessing. confidence should reflect how complete and well-sourced the research was."
    )


def _validate(profile: VendorRiskProfile) -> tuple[bool, str]:
    good_enough = profile.confidence >= 0.6 and len(profile.missing_information) <= 1
    gap = "; ".join(profile.missing_information) or "general additional detail"
    return good_enough, gap


config = UseCaseConfig(
    name="vendor_risk",
    output_schema=VendorRiskProfile,
    search_prompt=_search_prompt,
    extract_prompt=_extract_prompt,
    validate=_validate,
)
