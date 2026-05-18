from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

prompt_input="Write a 20-word motivational phrase to wake up"

response = client.chat.completions.create(
  model='gpt-5-mini',
  messages=[
    {"role": "user", "content": prompt_input}
  ]
)

print(response.choices[0].message.content)