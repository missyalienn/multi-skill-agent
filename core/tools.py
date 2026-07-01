"""
A ToolSpec is one registered tool.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class ToolCategory(str, Enum):
    HAND_CRAFTED = "hand_crafted"   # e.g. RAG over a vector DB you control
    API_BASED = "api_based"         # e.g. CRM lookup, custom REST call
    PLUG_IN = "plug_in"             # e.g. Claude's built-in web_search


@dataclass
class ToolSpec:
    name: str
    description: str  # this is what gets embedded for semantic routing
    category: ToolCategory
    executor: Callable[[str], str]  # (query) -> result text. Stubbed for non-plug-in tools until wired to real APIs.
