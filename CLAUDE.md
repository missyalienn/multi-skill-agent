# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## LangGraph currency

This is a client-facing reference architecture — LangGraph code must match current best practice,
not training-data assumptions. Before writing or reviewing anything in `core/workflow.py` or
`core/contracts.py`, verify against current docs (use a docs MCP if one is connected, otherwise
fetch docs.langchain.com directly). Don't assume state field patterns, entry-point APIs, or
schema/config conventions are still current — check first.

## Commands

```bash
# Setup
uv sync                                  # install deps from uv.lock

# Run the agent
python main.py vendor_risk "Acme Corp"
python main.py lead_enrichment "Acme Corp"

# Demo tool router (no API key needed)
python demo_tool_router.py

# Lint
ruff check .
ruff format .
```

Requires `ANTHROPIC_API_KEY` in `.env` (see `.env.example`). No test suite exists yet.

## Architecture

The framework separates **the engine** (`core/`) from **business use cases** (`use_cases/`). The engine never changes; adding a new use case means writing one `UseCaseConfig` in `use_cases/`.

### Core loop (LangGraph graph)

`core/workflow.py` wires three generic nodes into a self-correcting graph:

```
search → extract → validate ─(done)──▶ END
                       └──(retry)──▶ search
```

- **`search` node** — calls Claude with `web_search` tool; appends results to `GraphState.search_results`
- **`extract` node** — calls Claude to parse search results into the use case's Pydantic output schema
- **`validate` node** — runs `UseCaseConfig.validate()`; if the result is insufficient and retries remain, it writes a sharpened `search_query` and loops back

`GraphState` (`core/contracts.py`) is the only shared state object. It is use-case-agnostic; all use-case-specific shape lives in `UseCaseConfig.output_schema`.

### UseCaseConfig adapter pattern

Each file in `use_cases/` exports a single `config: UseCaseConfig` instance with:
- `output_schema` — a Pydantic `BaseModel` defining the structured output
- `search_prompt(target, refinement) -> str` — builds the search instruction
- `extract_prompt(target, results, schema_json) -> str` — builds the extraction instruction
- `validate(instance) -> (bool, str)` — returns `(good_enough, gap)` where `gap` sharpens the next search query on retry

`main.py` dynamically imports the use case module by name, so a new use case is immediately available as a CLI argument.

If adding a new use case ever requires touching `core/`, that's a defect in the adapter pattern —
flag it rather than working around it.

### Semantic Tool Selection (`core/tool_router.py`)

`ToolRouter` embeds each `ToolSpec.description` once at construction time and routes an incoming query by cosine similarity — no model call needed for routing. The default `TfidfEmbedder` is offline and key-free (demo-only). For production, implement the `Embedder` protocol (`embed(texts: list[str]) -> np.ndarray`) and pass an instance to `ToolRouter.__init__`. Voyage AI is the recommended embedding backend.

`ToolRouter` is currently standalone (see `demo_tool_router.py`). It is not yet wired into the main agent loop in `core/nodes.py`.

### Tool taxonomy (`core/tools.py`)

`ToolCategory` mirrors the three tool types:
- `HAND_CRAFTED` — RAG over a controlled vector DB (e.g. Pinecone)
- `API_BASED` — structured external API calls (e.g. firmographic lookup)
- `PLUG_IN` — provider-native tools (e.g. Claude's built-in `web_search`)