# %%
import os
import json

from openai import OpenAI
from dotenv import load_dotenv
import importlib
import prompts

importlib.reload(prompts)
from prompts import SYSTEM_PROMPT, build_postgres_sql_generate_prompt, build_sqlite_sql_generate_prompt

import db_conn
importlib.reload(db_conn)
from db_conn import query_data_base


import sqlite3

load_dotenv()

import httpx

OpenAPIKey=os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OpenAPIKey, http_client=httpx.Client(verify=False))
# print(f"openai key: {OpenAPIKey}")

USER_QUERY = f"""Give me the number of service requests generated for system ID 11060815, 175603. Also, determine the most frequent site issue at the sub-system level for these units.
"""

f"""
Tell me how many tickets opened for system 11060815, 175806? And what's the most problem(sub-system level) happened site issue of this system?
"""

f"""
Tell me about system 11060815/175678's problems. I want ALL tickets that opened for this system.
"""

# response = client.responses.create(
#     model="gpt-5.2",
#     input="Write a short bedtime story about a unicorn."
# )

# print(response.output_text)

# %%
try:
    system_prompt = SYSTEM_PROMPT
    print(system_prompt)
    response = client.chat.completions.create(
        model="gpt-5.2",
        messages=[
            {"role": "system", "content": system_prompt},
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

sql_system_prompt = build_postgres_sql_generate_prompt(filters_json_dump)
print(sql_system_prompt)

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


# %%
# for SQLite SQL
try:
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

sql_system_prompt = build_sqlite_sql_generate_prompt(filters_json_dump)

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

# %%
query_results = query_data_base(sql_result)
print(query_results)




# %%
