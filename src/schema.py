OUTPUT_SCHEMA = {
  "answer": "string - agent's answer",
  "confidence": "number - between 0.0 and 1.0",
  "actions": ["string - recommended actions list (empty list is valid)"],
}

REQUIRED_FIELDS = {'answer', 'confidence', 'actions'}

def validate_response(payload: dict) -> dict:
  """
  Check if the dict fulfills the contract schema. Return the dict if valid; otherwise, throw ValueError.
  """
  
  if not isinstance(payload, dict):
    raise ValueError(f"{payload} must be a dict. Got {type(payload).__name__}")

  missing = REQUIRED_FIELDS - payload.keys()

  if missing:
    raise ValueError(f"Missing values: {missing}")
  
  answer, confidence, actions = payload['answer'], payload['confidence'], payload['actions']

  if not isinstance(answer, str):
    raise ValueError(f"answer must be a string. Got {answer}.")
  
  if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0.0 <=confidence <=1.0:
    raise ValueError(f"confidence must be a number between 0.0 and 1.0. Got {confidence}.")
  
  if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
    raise ValueError(f"actions must be a list of strings. Got {actions}.")
  
  return payload