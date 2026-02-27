"""
Prompt 入口模块 —— 所有版本在这里集中配置，一目了然。
"""

from datetime import date
import yaml
import os
from prompt_loader import PromptLoader

# ──────────────────── 版本配置（改这里就行） ────────────────────
FILTER_VERSION = "v1"           # SQL filter prompt 用哪个版本
SQL_GEN_VERSION = "v1"          # SQL generator prompt 用哪个版本
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
print(schema_text)

# ──────────────────── 加载器 ────────────────────
loader = PromptLoader()  # 默认以自身所在目录为 prompts 根目录

# ──────────────────── System Prompt ────────────────────
SYSTEM_PROMPT = loader.load(
    "SQL_filters_generator", 
    "v1",
    today_str=today_str,
    schema_text=schema_text,
)
print(SYSTEM_PROMPT)


# ──────────────────── SQL 生成 Prompt ────────────────────
def build_sql_generate_prompt(filters_json: str) -> str:
    return loader.load(
        "SQL_generator", SQL_GEN_VERSION,
        filters_json=filters_json,
        schema_text=schema_text,
    )


def build_sqlite_sql_generate_prompt(filters_json: str) -> str:
    return loader.load(
        "SQLite_generator", SQLITE_GEN_VERSION,
        filters_json=filters_json,
        schema_text=schema_text,
    )