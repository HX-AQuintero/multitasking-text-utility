import json
from pathlib import Path
from openai import OpenAI

from schema import validate_response

PROMPT_PATH = Path(__file__).parent.parent / 'prompts' / 'main_prompt.txt'
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding='utf-8')


client = OpenAI()


def call_llm(prompt_input: str, max_retries: int = 1) -> tuple:
  """
  Call the model, parse, validate, and retry on failure. Returns (validated_dict, raw_response). Raises RuntimeError if retries exhausted.
  """

  attempt = 0
  last_error = None


  while attempt <= max_retries:
    messages = [
      {'role': 'system', 'content': SYSTEM_PROMPT},
      {'role': 'user', 'content': prompt_input}
    ]
    
    response = client.chat.completions.create(
      model='gpt-4o-mini-2024-07-18', #TODO! ADD THE REASON WHY THIS MODEL INTO REPORT FILE
      messages=messages,
      max_tokens=400, #TODO! ADD THE REASON WHY THIS AMOUNT OF TOKENS ARE CONSIDERED INTO REPORT FILE
      temperature=0.2, #TODO CHANGE VALUES 0.0-0.3 TO SEE CHANGES. PUT THAT INTO REPORT FILE
      response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content

    try:
      data = json.loads(raw_content)

    except json.JSONDecodeError as e:
      last_error = f"JSON parsing failed: {e}" #TODO REPORT THE REPARATION FIX PREVIOUSLY DEFINED (SEE SCREENSHOT)
      attempt += 1
      continue

    try:
      validated = validate_response(data)

    except ValueError as e:
      last_error = f"Schema validation failed: {e}"
      attempt += 1
      continue

    
    return validated, response
  
  raise RuntimeError(
    f"The model did not return a valid output after {max_retries + 1} retries. Last error: {last_error}"
  )