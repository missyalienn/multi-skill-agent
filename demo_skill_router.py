"""
Demonstrates Semantic Skill Selection across three tool categories
(hand-crafted RAG, API-based, plug-in web search) without needing any
live API keys -- the routing logic is the thing being demonstrated, not
the tool execution itself.

Run:
    python demo_skill_router.py
"""

from core.skill_router import SkillRouter
from core.tools import ToolSpec, SkillCategory


def _stub(label: str):
    def executor(query: str) -> str:
        return f"[{label} executed with query: {query!r}]"
    return executor


tools = [
    ToolSpec(
        name="vendor_knowledge_rag",
        description=(
            "Search our internal vector database of past vendor risk assessments, "
            "contracts, and compliance notes for information about a specific vendor "
            "we have worked with before."
        ),
        category=SkillCategory.HAND_CRAFTED,
        executor=_stub("Pinecone RAG lookup"),
    ),
    ToolSpec(
        name="company_lookup_api",
        description=(
            "Look up structured firmographic data -- industry, headcount, funding "
            "rounds, registered address -- for a company via a business data API."
        ),
        category=SkillCategory.API_BASED,
        executor=_stub("API call"),
    ),
    ToolSpec(
        name="web_search",
        description=(
            "Search the live web for recent news, articles, or public information "
            "that may not exist in our internal systems."
        ),
        category=SkillCategory.PLUG_IN,
        executor=_stub("Claude web_search tool"),
    ),
]

router = SkillRouter(tools)

test_queries = [
    "What did we note about this vendor's compliance posture last time we assessed them?",
    "What's the headcount and funding history for this company?",
    "Has there been any recent news about a data breach at this company?",
]

if __name__ == "__main__":
    for query in test_queries:
        ranked = router.select(query, top_k=3)
        print(f"\nQuery: {query}")
        for tool, score in ranked:
            print(f"  {score:.3f}  {tool.name}  ({tool.category.value})")
        top_tool, top_score = ranked[0]
        print(f"  -> ROUTED TO: {top_tool.name}")
        print(f"  -> {top_tool.executor(query)}")
