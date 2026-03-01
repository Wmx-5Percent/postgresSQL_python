"""
Prompt 入口模块 —— 所有版本在这里集中配置，一目了然。
"""

from datetime import date
import yaml
import os
try:
    from .prompt_loader import PromptLoader  # 作为包导入时
except ImportError:
    from prompt_loader import PromptLoader   # 直接运行时

from rag.retriever import Text2SQLRetriver

# ──────────────────── 版本配置（改这里就行） ────────────────────
SQL_FILTER_PROMPT_VERSION = "v2"           # SQL filter prompt 用哪个版本
POSTGRES_SQL_GEN_PROMPT_VERSION = "v3"          # SQL generator prompt 用哪个版本
SQLITE_GEN_VERSION = "v1"       # SQLite generator prompt 用哪个版本

# ──────────────────── 公共变量 ────────────────────
today_str = date.today().strftime("%Y/%b/%d")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
yaml_path = os.path.join(BASE_DIR, "..", "schema_compact.yaml")  # 上级目录

with open(yaml_path, "r", encoding="utf-8") as f:
    schema_data = yaml.safe_load(f)

schema_lines = []
for col_name, col_info in schema_data.get("columns", {}).items():
    schema_lines.append(f"- {col_name} ({col_info['type']}): {col_info['desc']}")
schema_text = '\n'.join(schema_lines)
# print(schema_text)

# ──────────────────── 加载器 ────────────────────
loader = PromptLoader()  # 默认以自身所在目录为 prompts 根目录

# ──────────────────── System Prompt ────────────────────
SYSTEM_PROMPT = loader.load(
    "SQL_filters_generator", 
    SQL_FILTER_PROMPT_VERSION,
    today_str=today_str,
    schema_text=schema_text,
)
# print(SYSTEM_PROMPT)

_retriever = None
def _get_retriever() -> Text2SQLRetriver:
    global _retriever
    if _retriever is None:
        _retriever = Text2SQLRetriver()
    return _retriever

# ──────────────────── SQL 生成 Prompt ────────────────────
def build_postgres_sql_generate_prompt(filters_json: str) -> str:
    return loader.load(
        "SQL_Postgres_generator", 
        POSTGRES_SQL_GEN_PROMPT_VERSION,
        filters_json=filters_json,
        schema_text=schema_text,
    )


def build_sqlite_sql_generate_prompt(filters_json: str) -> str:
    return loader.load(
        "SQLite_generator", SQLITE_GEN_VERSION,
        filters_json=filters_json,
        schema_text=schema_text,
    )

def build_rag_enhanced_system_prompt(question: str) -> str:
    retriever = _get_retriever()
    rag_context = retriever.build_rag_context([question])
    
    if rag_context:
        return SYSTEM_PROMPT + "\n" + rag_context
    else:
        return SYSTEM_PROMPT

def build_rag_enhanced_postgres_sql_generate_prompt(question: str, filters_json: str) -> str:
    raw_sql_generate_prompt = loader.load(
        "SQL_Postgres_generator", 
        POSTGRES_SQL_GEN_PROMPT_VERSION,
        filters_json=filters_json,
        schema_text=schema_text,
    )

    retriever = _get_retriever()
    rag_context = retriever.build_rag_context([question])

    if rag_context:
        return raw_sql_generate_prompt + "\n" + rag_context
    else:
        return raw_sql_generate_prompt