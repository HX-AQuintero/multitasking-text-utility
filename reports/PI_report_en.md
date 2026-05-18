# Project Integrator Report — Multitasking Text Utility

## 1. Overview

This project implements a customer support assistant that processes user 
questions and returns structured JSON responses (`answer`, `confidence`, 
`actions`), while logging per-execution metrics for cost and performance 
monitoring. The system is built on the OpenAI Chat Completions API and 
demonstrates an end-to-end LLM integration with explicit observability and 
defensive validation.

## 2. Architecture

The application follows a modular layered design with single-responsibility 
modules and unidirectional dependencies:

```
User input
│
▼
run_query.py   ──── orchestrator: timing, metrics, CLI
│
▼
llm_client.py  ──── OpenAI integration + JSON parsing + retry
│
▼
schema.py      ──── contract validation
```
- **`schema.py`** defines and enforces the output contract. Pure logic; no 
  I/O, no external dependencies.
- **`llm_client.py`** is the only module aware of OpenAI. It loads the 
  system prompt from `prompts/main_prompt.txt`, calls the API, parses the 
  response, validates it against the schema, and retries on failure.
- **`metrics.py`** computes estimated cost and persists per-execution rows 
  to `metrics/metrics.csv`. `estimate_cost_usd` is a pure function, making 
  it trivially testable.
- **`run_query.py`** orchestrates the flow: loads environment variables, 
  measures latency, calls the model, logs metrics, and prints the validated 
  JSON.

This separation makes the codebase easy to test (validation and cost logic 
have no external dependencies) and easy to extend — swapping OpenAI for 
another provider would only require changes in `llm_client.py`.

## 3. Prompting technique: few-shot

After an initial **zero-shot baseline**, four few-shot examples were added 
to the system prompt, each covering a distinct response pattern:

1. **Trivial FAQ** (high confidence, empty actions).
2. **Standard case with concrete actions** (high confidence, populated list).
3. **Out-of-scope query** (very low confidence, escalation actions).
4. **Ambiguous request** (mid confidence, clarification action).

### Rationale

Few-shot was chosen for two reasons:
- The task requires a **consistent JSON schema across diverse inputs**, 
  which the course material identifies as the canonical use case for 
  few-shot prompting.
- During zero-shot baseline experiments, the model self-reported 
  `confidence` in a narrow range (0.85–0.95) regardless of question 
  difficulty. The legal-escalation example was specifically chosen to 
  calibrate the model toward using the lower end of the confidence range 
  when appropriate.

### Iteration evidence

| Iteration | Behavior | Observation |
|---|---|---|
| Zero-shot baseline | `confidence` clustered in 0.85–0.95 | Field was decorative, not informative |
| Few-shot with calibrated examples | `confidence` varies meaningfully | Confidence now reflects question difficulty |

## 4. Key technical decisions

| Decision | Value | Justification |
|---|---|---|
| Model | `gpt-4o-mini` | Lowest-cost model in the family; the task is structured extraction (no deep reasoning needed). Recommended approach in course material: start small, scale only when justified. |
| `temperature` | `0.2` | Within the 0.0–0.3 range recommended for extraction/classification. Low enough for stable JSON output, high enough to avoid degenerate determinism. |
| `max_tokens` | `400` | Typical JSON responses consume 80–120 tokens. The 400 ceiling provides margin for longer answers without enabling verbosity that would inflate cost. |
| `response_format` | `{"type": "json_object"}` | API-level guarantee that the response is parseable JSON, reducing the need for repair logic. |
| Retry strategy | 1 retry, identical parameters | Covers transient parse failures. Identical parameters avoid masking systemic prompt problems behind escalation logic. |
| Metrics persistence | CSV (append-only) | Easy to inspect in spreadsheets; readable in the report; no external dependencies beyond stdlib. |
| Validation | Custom validator in `schema.py` | Decouples contract checks from the LLM client, making both modules independently testable. |

## 5. Sample metrics

Five representative executions, taken directly from `metrics/metrics.csv`:

| Question type | Prompt tokens | Completion tokens | Latency (ms) | Cost (USD) |
|---|---|---|---|---|
| Trivial FAQ (password reset) | 94 | 64 | 3242.0 | 0.0000525 |
| Same question, second call | 94 | 62 | 2043.1 | 0.0000513 |
| Locked account | 94 | 78 | 2511.4 | 0.0000609 |
| Legal escalation request | 94 | 71 | 2378.6 | 0.0000567 |
| Ambiguous (logo color) | 94 | 69 | 2204.8 | 0.0000555 |

### Observations

- **Per-call cost is negligible.** Even at the upper end (~$0.00006), 
  reaching $1.00 in spend requires ~17,000 calls. Cost only becomes 
  meaningful at scale.
- **Latency varied 1.2 seconds across identical inputs**, reflecting 
  network and OpenAI-side variability. Single measurements are unreliable; 
  averages over N executions are required for meaningful comparison.
- **Prompt tokens were stable** at 94 across all zero-shot calls; with 
  few-shot prompting active, this constant baseline rises (since the 
  examples are part of every prompt) — a deliberate tradeoff of cost for 
  output quality.

## 6. Tradeoffs and limitations

- **`confidence` is self-reported.** The model declares its own confidence; 
  there is no external calibration. Few-shot examples nudge the model 
  toward appropriate ranges, but no statistical guarantee is provided.
- **No moderation layer.** Adversarial prompts (e.g., prompt injection 
  attempts) are not detected or filtered. A natural extension would be a 
  pre-processing safety check as described in course materials.
- **Single-provider lock-in.** The current design assumes OpenAI. Migrating 
  to another provider (Claude, Gemini) would require changes only in 
  `llm_client.py`, but no provider abstraction layer was implemented.
- **No RAG.** Answers come purely from the model's pre-trained knowledge. 
  For a production support assistant, grounding in a company-specific 
  knowledge base would be the highest-impact next step.

## 7. Possible improvements

- **Confidence calibration via evaluation set.** Build a small labeled 
  dataset of (question, expected_confidence_range) and measure calibration 
  empirically. Adjust few-shot examples until calibration improves.
- **Moderation middleware.** Add a pre-call check for prompt injection 
  patterns and a post-call PII redaction step.
- **Provider abstraction.** Introduce an `LLMProvider` interface to support 
  failover between OpenAI, Claude, and Gemini.
- **RAG integration.** Connect to a vector store with company documentation 
  so the assistant grounds its answers in retrieved context rather than 
  parametric memory.
- **Streaming responses.** For better UX, stream tokens as they arrive 
  instead of waiting for the complete JSON. Requires schema validation 
  after the stream completes.

## 8. Self-evaluation against the project rubric

| Requirement | Status |
|---|---|
| Executable script returning valid JSON | ✅ `python src/run_query.py "..."` |
| Per-execution metrics (tokens, latency, cost) | ✅ Persisted to `metrics/metrics.csv` |
| Documented prompt engineering technique | ✅ Few-shot with calibration rationale (Section 3) |
| At least one automated test | ✅ 16 tests in `tests/test_core.py` (schema, cost, mocked log_run) |
| README + report | ✅ This document + `README.md` |
| Documented setup with `.env.example` | ✅ |
| Safety/moderation (bonus) | ❌ Not implemented; documented as future work |