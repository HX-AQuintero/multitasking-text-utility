import csv
from datetime import datetime, timezone
from pathlib import Path

METRICS_PATH = Path(__file__).parent.parent / "metrics" / "metrics.csv"

# Pricing per 1M tokens gpt-4o-mini-2024-07-18 (as of 2026-05-18)
PRICE_INPUT_PER_1M = 0.15
PRICE_OUTPUT_PER_1M = 0.60

FIELDNAMES = [
  "timestamp", "model", "technique", "temperature", "prompt_tokens", 
  "completion_tokens", "total_tokens", "latency_ms", "estimated_cost_usd"
]

def estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
  """
  Calculate estimated cost in USD for gpt-4o-mini-2024-07-18
  """

  cost = (prompt_tokens / 1_000_000) * PRICE_INPUT_PER_1M + (completion_tokens / 1_000_000) * PRICE_OUTPUT_PER_1M

  return cost

# Metrics
def log_run(response, latency_ms: float, technique: str, temperature: float) -> dict:
  """
  Make the metrics row from an OpenAI response and keep it (persistency)
  """

  prompt_tokens = response.usage.prompt_tokens
  completion_tokens = response.usage.completion_tokens
  total_tokens = response.usage.total_tokens

  row = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "estimated_cost_usd": round(estimate_cost_usd(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),6),
    "model": response.model,
    "technique": technique,
    "temperature": temperature,
    "prompt_tokens": prompt_tokens,
    "completion_tokens": completion_tokens,
    "total_tokens": total_tokens,
    "latency_ms": latency_ms
  }

  _append_row(row)

  return row

def _append_row(row: dict) -> None:
  """
  Add a row to the metrics CSV file. Create the file if does not exist
  """
  METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
  file_exists = METRICS_PATH.exists()

  with open(METRICS_PATH, 'a', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    if not file_exists:
      writer.writeheader()
    writer.writerow(row)