import os
import sys
import time

# Dev-only: allow running this file interactively from evals/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import csv
from typing import List, Dict
import json
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from prompts import (
    SYSTEM_PROMPT, 
    build_postgres_sql_generate_prompt,
    build_rag_enhanced_postgres_sql_generate_prompt,
    build_rag_enhanced_system_prompt
)   
from prompts.prompt_loader import PromptLoader

load_dotenv()

OpenAIKey = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OpenAIKey)
model = "gpt-5.2"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(BASE_DIR, "..", "tests", "Text2SQL_Test_Questions_Single_Value_RealData.csv")
print(csv_path)

HOST=os.getenv("PostgresSQLHost")
PORT=os.getenv("PostgresSQLPort")
DATABASE=os.getenv("PostgresSQLDBName")
USER=os.getenv("PostgresSQLUser")
PASSWORD=os.getenv("PostgresSQLPwd")
CONN_TIMEOUT=30

engine = create_engine(
    f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}",
    pool_pre_ping=True,
)

def load_test_cases_from_csv(csv_path: str) -> List[Dict]:
    res = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['ID'] = int(row['ID'])
            row['GroundTruthValue'] = int(row['GroundTruthValue'])
            res.append(row)

    return res

def call_llm(client, model: str, system_prompt: str, user_message: str) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print("called llm failed:", e)
        return None

def execute_sql(sql_query: str) -> dict:
    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            rows = result.fetchall()
            columns = list(result.keys())
            if not rows:
                return {
                    "columns": columns, 
                    "value": [], 
                    "error": None}
            return {
                "columns": columns,
                "value": [list(row) for row in rows],
                "error": None
            }
    except Exception as e:
        print("queried database failed:", e)
        return {"value": None, "error": str(e)}

def write_agent_result_to_csv(results: List[Dict], output_path: str) -> None:
    if not results:
        print("No results to write")
        return
    
    fieldnames = list(results[0].keys())
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Results saved to {output_path}")

    

if __name__ == "__main__":
    filter_version = "v2"
    sql_gen_version = "v3"

    cases = load_test_cases_from_csv(csv_path)
    print(f"loaded {len(cases)} test cases")

    correct = 0
    total = len(cases)

    for case in cases:
        question = case["Question_English"]
        print(f"--- #{case['ID']} ---")

        # 生成sql filters
        sql_filters = call_llm(client, model, build_rag_enhanced_system_prompt(question), question)
        case["Filters_JSON"] = sql_filters
        time.sleep(1)

        # 生成sql
        if sql_filters is not None:
            sql = call_llm(client, model, build_rag_enhanced_postgres_sql_generate_prompt(question, sql_filters), question)
        else:
            sql = "sql filters is none"
        case["Generated_SQL"] = sql

        # 执行sql
        query_result = execute_sql(sql)

        llm_value = None
        if query_result["value"]:
            llm_value = query_result["value"][0][0]

        case["LLM_SQL_Value"] = llm_value
        case["Error_Message"] = query_result["error"]

        # 比较结果
        is_correct = (llm_value == case["GroundTruthValue"])
        case["Is_Correct"] = is_correct
        case["Filter_Version"] = filter_version
        case["SQL_Gen_Version"] = sql_gen_version

        if is_correct:
            correct += 1
            print(f" expected={case['GroundTruthValue']}, got={query_result['value']}")
        else:
            print(f" expected={case['GroundTruthValue']}, got={query_result['value']}, error={query_result['error']}")

    # 打印汇总
    print(f"\n{'='*50}")
    print(f"Accuracy: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"Filter Version: {filter_version}")
    print(f"SQL Gen Version: {sql_gen_version}")
    output_path = os.path.join(BASE_DIR, "results", f"eval_filter_with_RAG.csv")
    write_agent_result_to_csv(cases, output_path)