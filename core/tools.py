"""
A ToolSpec is one registered skill. The `category` field maps directly to
the book's skill taxonomy (Ch.4): hand_crafted (e.g. RAG over Pinecone),
api_based (custom client-executed calls), or plug_in (provider-native
tools like Claude's web_search).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class SkillCategory(str, Enum):
    HAND_CRAFTED = "hand_crafted"   # e.g. RAG over a vector DB you control
    API_BASED = "api_based"         # e.g. CRM lookup, custom REST call
    PLUG_IN = "plug_in"             # e.g. Claude's built-in web_search


@dataclass
class ToolSpec:
    name: str
    description: str  # this is what gets embedded for semantic routing
    category: SkillCategory
    executor: Callable[[str], str]  # (query) -> result text. Stubbed for non-plug-in tools until wired to real APIs.
