# Audit Report: LangGraph Architecture Currency & Layer Readiness

## Context
Goal is to evolve this repo from its current 2-layer shape (engine `core/` + use-case configs `use_cases/`) into a 3-layer reference architecture: ENGINE (generic graph/checkpointer/tracing/interrupt scaffolding) → CAPABILITY (composable nodes: retry, structured output, tool use, HITL, fan-out) → USE CASE (config only). This report is the audit requested before any implementation: coupling scan, capability inventory, and a verdict on `tool_router.py`'s fit. No code changes were made. Findings below are doc-verified against docs.langchain.com (fetched live; no docs MCP was connected this session).

---

## 1. Coupling audit (core/ → use_cases/)

**Certain — verified by full read of every core/ file plus both use_cases files.**

**No coupling found.** `core/contracts.py`, `core/nodes.py`, `core/workflow.py` are use-case-agnostic: all three node factories (`make_search_node`, `make_extract_node`, `make_validate_node`) operate purely through `UseCaseConfig` callables (`search_prompt`, `extract_prompt`, `output_schema`, `validate`, `model`). No imports of `use_cases.*`, no string literals naming either use case, no conditionals keyed on `config.name`. The dependency direction is already correct (use_cases → core, never reverse). This is good news — the adapter pattern genuinely holds and needs no coupling-related restructure.

One cosmetic residue: `main.py:17` still calls the imported module `domain_module` (`domain_module = importlib.import_module(...)`) — a leftover from the pre-rename `domains/` → `use_cases/` migration (commits `ab4023f`, `2c0b3be`). Not coupling, just stale naming.

---

## 2. Capability inventory

| Capability | Status | Evidence | Target layer |
|---|---|---|---|
| Validation-gated retry | **Exists** | `core/nodes.py:65-85` (`make_validate_node`), `core/workflow.py:22-24` (conditional edge) | Currently engine; belongs in capability |
| Structured output validation | **Exists, non-idiomatic** | `core/nodes.py:52-58` — prompts model for JSON, strips ``` fences, `model_validate_json` | Currently engine; belongs in capability |
| Multi-step tool use | **Missing** | `core/nodes.py:28-33` is one `messages.create` call with `web_search_20250305`; no loop over `tool_use`/`tool_result` blocks | Capability (new) |
| HITL interrupt | **Missing** | repo-wide grep for `interrupt`: no matches | Capability (new) |
| Checkpointing | **Missing** | `core/workflow.py:26` `graph.compile()` takes no `checkpointer=` | Engine |
| Tracing | **Missing** | no `LANGCHAIN_TRACING_V2`/callbacks anywhere; `langsmith` only present as a transitive lockfile dep, unused | Engine |
| Fan-out (Send API) | **Missing** | no `Send(` usage; `workflow.py` is strictly linear/conditional | Capability (new) |

---

## 3. FIX — non-idiomatic vs. current best practice

1. **`core/workflow.py:19`** — `graph.set_entry_point("search")` still works but is legacy syntax.
   **Doc-verified fix:** use `graph.add_edge(START, "search")` (`from langgraph.graph import START`) — docs state this is "the recommended modern syntax," consistent with the existing `add_edge(..., END)` already in the file.

2. **`core/workflow.py:5,13`** — `import langgraph.graph as graph` is immediately shadowed by the local `graph = StateGraph(GraphState)` on line 13. Harmless today (the module alias is never used after import) but fragile — any future reference to the `graph` module inside `build_graph` will silently resolve to the StateGraph instance instead.

3. **`core/nodes.py:52-58`** (`make_extract_node`) — manual JSON-prompt + fence-stripping + `model_validate_json` is the "not recommended" path per current LangChain guidance. **Doc-verified fix:** current best practice for Claude is provider-native structured output (schema passed directly, auto-selected `ProviderStrategy` for Anthropic models) rather than prompt-and-parse.

   **Decision:** migrate model integration from the raw `anthropic` SDK to LangChain (`ChatAnthropic` / `init_chat_model`) as part of this reference architecture. This resolves FIX #3 directly — extraction uses LangChain-native `response_format` instead of manual JSON parsing — and also unblocks ADD #1 (multi-step tool use, see below) via LangChain's native tool binding instead of a hand-rolled dispatch loop.

4. **`core/workflow.py:26`** — `compile()` with no `checkpointer=` argument. Even before HITL/interrupt work lands, current best practice is to compile with an explicit checkpointer (e.g. `InMemorySaver` for dev) — interrupts and multi-turn resume are structurally impossible to bolt on later without changing `build_graph`'s signature and every call site, so this is cheaper to fix now than after use cases multiply.

5. **`main.py:17`** — `domain_module` naming is stale relative to the completed `domains/` → `use_cases/` rename elsewhere in the codebase. Cosmetic, low priority.

---

## 4. ADD — missing capabilities, target layer, doc-verified pattern

1. **Multi-step tool use** → CAPABILITY. **Decision:** built LangChain-native, per the model-integration migration above — bind tools directly to the `ChatAnthropic` model and use LangGraph's prebuilt `ToolNode`/agent-loop shape, not a hand-rolled `tool_use`/`tool_result` dispatch loop against the raw SDK.

   **Decision on `tool_router.py`:** does **not** get wired into this default tool-use path. At current/expected scale (~5 tools), all tools are bound directly to the model — no retrieval/routing layer needed; that's the standard LangChain/LangGraph tool-calling pattern for small tool counts. `tool_router.py` is reclassified as an **optional** capability module, to be documented as: "swap in when tool count grows beyond what fits in one prompt (rule of thumb: tens+)." This is the same problem LangGraph's own `langgraph-bigtool` addresses — `tool_router.py` is this repo's lightweight, dependency-light version of that pattern, not a fit for the default path at current scope. See §5 for its placement.

2. **HITL interrupt** → CAPABILITY. `from langgraph.types import interrupt, Command` — calling `interrupt(payload)` inside a node pauses the graph and surfaces `payload` to the caller; resuming requires `Command(resume=value)` on the next `.invoke`/`.stream` call, and **requires a checkpointer** (see FIX 4 — this is why checkpointing must land first).

3. **Checkpointing** → ENGINE. `from langgraph.checkpoint.memory import InMemorySaver`; pass via `graph.compile(checkpointer=InMemorySaver())`; callers must pass `{"configurable": {"thread_id": ...}}` in config. Production swaps to `SqliteSaver`/`PostgresSaver` without changing `build_graph`.

4. **Tracing** → ENGINE, but note it's primarily *configuration* (`LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, optional `LANGCHAIN_PROJECT`), not code — the engine doesn't need new abstractions, just documented env wiring in `.env.example` and a README note.

5. **Fan-out** → CAPABILITY. `from langgraph.types import Send`; a conditional-edge function returns `[Send("node_name", {...state...}) for item in items]`; parallel branch results merge back via `Annotated[list, operator.add]` (or similar reducer) on the relevant `GraphState` field. Directly applicable if a use case ever needs to research multiple targets or multiple search angles concurrently before extraction.

---

## 5. RESTRUCTURE — layer moves

**No use-case decoupling work needed** (§1 — core/ is already clean). The restructure is about splitting `core/` itself, which today conflates engine and capability:

- **`core/nodes.py` mixes engine and capability in one file.** `make_search_node`/`route_after_validate` are genuine engine control-flow (generic, use-case-agnostic graph plumbing). But the retry-gating logic inside `make_validate_node` and the schema-parse/validate logic inside `make_extract_node` are exactly the two capabilities the target architecture wants as named, reusable capability nodes — they're just not factored out yet. Recommend splitting into a new `capability/` package (e.g. `capability/retry.py`, `capability/structured_output.py`), with `core/nodes.py` reduced to thin factories that compose capability functions, parameterized by `UseCaseConfig` exactly as today (same discipline that kept core/ decoupled — extend it to capability/, not just engine/).

- **`tool_router.py` + `tools.py` are currently in `core/` (engine) but don't belong there.** They implement tool *selection* (embed descriptions, cosine-similarity routing) — this is domain-adjacent orchestration logic a capability node would call, not generic graph/checkpointer/tracing scaffolding. Verdict for task 3: **not a fit for engine, and not itself the default tool-use capability node either** — per the decision above, the default multi-step tool-use path (ADD-1) binds all tools directly to the model and does not consume `ToolRouter` at current scale (~5 tools). Recommend moving both files to `capability/` (e.g. `capability/tool_selection.py`) as an **optional, documented-but-unwired** module — the same role LangGraph's own `langgraph-bigtool` plays upstream — for future use if/when tool count grows into the tens+. Currently `ToolRouter` is unwired into the real graph at all (only consumed by `demo_tool_router.py`), so this move has zero blast radius on the working pipeline.

- **Engine (`core/`) after restructure** keeps: `contracts.py` (`GraphState`/`UseCaseConfig` — unchanged), `workflow.py` (graph wiring, now with `checkpointer=` and `START` edge — FIX 1/4), and a slimmed `nodes.py` limited to pure control-flow factories. New engine surface area for interrupt/tracing scaffolding described in ADD 2–4 lands here too, since those are inherently graph-lifecycle concerns, not per-use-case swappable logic.

- **Use case layer (`use_cases/`)** is unaffected by this restructure — `UseCaseConfig`'s shape doesn't need to change for any of the above; capability nodes should be composed by `core/workflow.py`/`core/nodes.py` at build time, not exposed as something a use-case file configures directly, to keep `use_cases/*.py` as pure config (per the existing, correctly-enforced discipline).

---

## 6. Build order

Sequenced on the dependency already identified in ADD #2/#3 (interrupt requires a checkpointer) and on doing the engine/capability split before adding new capability nodes to it:

1. **Trivial FIX items** (#1 `START` edge syntax, #2 unused-import shadow, #5 `main.py` `domain_module` naming) — do first, no dependencies, clears noise before real work.
2. **Tracing** (ADD-4, LangSmith) — config-only; do early so all subsequent steps are traced as they're built.
3. **Checkpointer** (FIX #4 / ADD-checkpointing) — `InMemorySaver` now, swappable to Sqlite/Postgres later.
4. **Restructure `core/` into engine vs. capability** (§5) — before adding new capability nodes, so they land in the right place the first time.
5. **HITL interrupt** (ADD-2) — depends on #3.
6. **Multi-step tool use** (ADD-1) — LangChain-native, all tools bound directly to the model, no router (per §4/§5 decisions above).

**Cut from v1 scope:** Fan-out / Send API (ADD-5) is not being implemented. No current use case requires parallel dispatch; document in the README as "designed for, intentionally out of scope."
