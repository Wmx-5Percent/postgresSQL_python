import os
import json

from openai import OpenAI
from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT, build_sql_generate_prompt

load_dotenv()

OpenAPIKey=os.getenv("OPENAI_API_KEY")

print(f"openai key: {OpenAPIKey}")

USER_QUERY = f"""
Tell me about system 11060815/175678's problems.
"""


try:
    client = OpenAI(api_key=OpenAPIKey)

    response = client.chat.completions.create(
        model="gpt-5.2",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_QUERY}
        ] 
    )

    result = response.choices[0].message.content
    print(f"original llm response")
    print("="*70)
    print(result)
    print("="*70)

    print(f"json loaded result")
    print("="*70)
    filters = json.loads(result)
    filters_json_dump = json.dumps(filters, indent=2)
    print("="*70)


    print(f"successfully connected to openai api!")
except Exception as e:
    print("connect with openai fail:", e)

sql_system_prompt = build_sql_generate_prompt(filters_json_dump)

response2 = client.chat.completions.create(
    model="gpt-5.2",
    messages=[
        {"role": "system", "content": sql_system_prompt},
        {"role": "user", "content": USER_QUERY}  
    ]
)

sql_result = response2.choices[0].message.content
print("step2: SQL =====")
print(sql_result)