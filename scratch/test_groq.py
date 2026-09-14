import sys
import os
from dotenv import load_dotenv
from groq import Groq

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
api_key = os.getenv('GROQ_API_KEY')
print("Testing GROQ API KEY:", api_key[:10] + "...")

client = Groq(api_key=api_key)

candidate_models = ['groq/compound', 'qwen/qwen3.6-27b', 'openai/gpt-oss-120b', 'groq/compound-mini']

for model_id in candidate_models:
    try:
        res = client.chat.completions.create(
            model=model_id,
            messages=[{'role': 'user', 'content': 'Respond with JSON: {"status": "ok"}'}],
            response_format={'type': 'json_object'}
        )
        print(f"SUCCESS with model: {model_id}")
        print("Response:", res.choices[0].message.content)
        break
    except Exception as e:
        print(f"FAILED with model {model_id}: {e}")
