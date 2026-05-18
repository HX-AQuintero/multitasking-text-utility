import json, sys, time
from dotenv import load_dotenv

load_dotenv()

from llm_client import call_llm
from metrics import log_run

TECHNIQUE = "zero-shot"
TEMPERATURE = 0.2

def run(prompt_input: str) -> dict:
  """
  Orchestrate the end-to-end flow. Returns the dict validated.
  """
  start = time.perf_counter()
  validated, response = call_llm(prompt_input=prompt_input)
  latency_ms = (time.perf_counter() - start) * 100

  log_run(response, latency_ms, technique=TECHNIQUE, temperature=TEMPERATURE)

  return validated

if __name__ == "__main__":
  question = sys.argv[1] if len(sys.argv) > 1 else input("Question: ")
  result = run(question)
  print(json.dumps(result, indent=2, ensure_ascii=False))