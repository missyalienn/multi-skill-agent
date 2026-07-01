# Multi-Skill Agent Framework

A reusable agentic engine, built around three pieces: a domain-agnostic
search → extract → validate → retry loop, a `DomainConfig` adapter pattern
so new business use cases are a single config file (not a rewrite), and
Semantic Skill Selection for routing between multiple tools.

## Structure

- `core/` — the engine. Never changes between use cases.
  - `contracts.py` — `GraphState`, `DomainConfig`
  - `nodes.py` — generic search/extract/validate node implementations
  - `graph.py` — LangGraph wiring with the self-correcting retry edge
  - `tools.py` — `ToolSpec`, `SkillCategory` (hand-crafted / API-based / plug-in)
  - `skill_router.py` — Semantic Skill Selection (see below)
- `domains/` — business use cases, each a config file: schema + prompts + validation rule
  - `vendor_risk.py`
  - `lead_enrichment.py`
- `main.py` — CLI: `python main.py <domain> "<target>"`
- `demo_skill_router.py` — standalone, runnable, zero-API-key demo of skill routing

## Semantic Skill Selection (core/skill_router.py)

Per *Building Applications with AI Agents* (early release), Ch. 5: rather
than handing the model every tool on every call, embed each tool's
description once, embed the incoming query, and route by cosine
similarity to the most relevant tool(s) before calling anything. The
book calls this the most common and recommended skill-selection pattern.

`demo_skill_router.py` proves this routes correctly across the three
skill categories from Ch. 4 (hand-crafted RAG, API-based, plug-in web
search) — runnable with zero API keys, since the routing logic itself
needs no live calls.

```bash
pip install -r requirements.txt
python demo_skill_router.py
```

**Known limitation, stated honestly:** the default `TfidfEmbedder` is
keyword-overlap, not true semantic embedding — it's a free, offline
stand-in so the demo runs without credentials. It mis-routes on queries
that share no vocabulary with the right tool's description (see the
third example query in the demo output). Production should swap in a
real embedding model (Voyage AI — Anthropic's recommended partner — or
OpenAI/Cohere embeddings) behind the same `Embedder` interface; nothing
else in `SkillRouter` changes.

## Next steps (not yet built)

- Wire `SkillRouter` into `core/nodes.py` so `gather_node` actually
  selects + calls tools mid-loop, instead of routing being a standalone
  demo
- Replace `TfidfEmbedder` with a real embedding model
- Wire the `vendor_knowledge_rag` tool to a real Pinecone index
- Add Hierarchical Skill Selection if/when the tool count grows enough
  to need it (book's explicit guidance: not needed yet)
