# Multitasking Text Utility — Module 1 Integrative Project

A customer support assistant that receives a question and returns a structured 
JSON response (`answer`, `confidence`, `actions`), while logging per-execution 
metrics (tokens, latency, estimated cost).

## Stack

- **Language:** Python 3.10+
- **Model:** `gpt-4o-mini` via OpenAI Chat Completions API
- **JSON enforcement:** `response_format={"type": "json_object"}`
- **Prompting technique:** zero-shot (system prompt with explicit schema 
  description)
- **Schema validation:** custom validator in `src/schema.py`
- **Resilience:** automatic retry (1 attempt) on JSON parse or schema 
  validation failure

## Project structure
```
├── prompts/
│   └── main_prompt.txt        # System prompt (treated as code)
├── src/
│   ├── schema.py              # Output contract validator
│   ├── llm_client.py          # OpenAI integration layer
│   ├── metrics.py             # Cost calculation and CSV persistence
│   └── run_query.py           # Entry point / orchestrator
├── metrics/
│   └── metrics.csv            # Per-execution metrics (auto-generated)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

1. Clone the repository.
2. Create and activate a virtual environment:
```bash
   python -m venv .venv
   source .venv/bin/activate     # Linux/Mac
   .venv\Scripts\activate        # Windows
```
3. Install dependencies:
```bash
   pip install -r requirements.txt
```
4. Copy `.env.example` to `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-proj-...
```

## Usage

Pass the question as a CLI argument:

```bash
python src/run_query.py "How do I reset my password?"
```

Or run interactively (the script will prompt for input):

```bash
python src/run_query.py
```

The script prints the validated JSON response to stdout and appends one row 
to `metrics/metrics.csv`.

### Example output

```json
{
  "answer": "To reset your password, go to the login page and click 'Forgot password?'. Follow the instructions sent to your registered email.",
  "confidence": 0.95,
  "actions": []
}
```

## Output contract

Every response is validated against the following schema:

| Field | Type | Description |
|---|---|---|
| `answer` | string | Response intended for the support agent |
| `confidence` | number (0.0–1.0) | Model's self-reported confidence |
| `actions` | list of strings | Recommended actions (empty list is valid) |

Responses that fail JSON parsing or schema validation trigger one automatic 
retry. If both attempts fail, the script raises `RuntimeError` with the last 
error message.

## Metrics

Each execution appends a row to `metrics/metrics.csv` with the following 
fields:

| Field | Source |
|---|---|
| `timestamp` | UTC ISO 8601, generated locally |
| `model` | From `response.model` |
| `technique` | Constant (`zero-shot`) |
| `temperature` | Constant (`0.2`) |
| `prompt_tokens` | From `response.usage.prompt_tokens` |
| `completion_tokens` | From `response.usage.completion_tokens` |
| `total_tokens` | From `response.usage.total_tokens` |
| `latency_ms` | Measured with `time.perf_counter()` |
| `estimated_cost_usd` | Computed from token counts and current pricing |

### Cost estimation

Cost is computed using OpenAI's published pricing for `gpt-4o-mini` (as of 
2026-05): $0.15 per 1M input tokens and $0.60 per 1M output tokens. Pricing 
constants are defined in `src/metrics.py`.

## Key design decisions

- **`gpt-4o-mini`** was chosen for its balance of cost and latency, matching 
  the structured-extraction nature of the task. No deep reasoning is required.
- **`temperature=0.2`** keeps outputs deterministic enough for stable JSON 
  while allowing minimal variation. Recommended range for 
  extraction/classification per course materials.
- **`max_tokens=400`** sized to accommodate a typical JSON response 
  (≈80–120 tokens) with margin for longer answers, without enabling 
  unnecessary verbosity.
- **`response_format=json_object`** provides API-level guarantee that the 
  output is parseable JSON, reducing the need for repair logic.
- **Single retry on failure** covers transient issues without masking 
  systemic prompt problems.

## Known limitations

- `confidence` is self-reported by the model and not well-calibrated in the 
  zero-shot setup; values tend to cluster in the 0.85–0.95 range regardless 
  of question difficulty. Calibration via few-shot examples is a natural 
  next step.
- No moderation or adversarial-input handling implemented in this version.
- Pricing constants are hardcoded; if OpenAI changes pricing, update 
  `src/metrics.py`.

## Reproducing metrics

After running the script multiple times, open `metrics/metrics.csv` in any 
spreadsheet tool or process programmatically. All values can be recomputed 
from token counts and the pricing constants in `src/metrics.py`.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key for the Chat Completions endpoint |