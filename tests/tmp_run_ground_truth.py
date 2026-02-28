"""
临时脚本：从 Text2SQL_Test_Questions.csv 中读取每条 PostgreSQL 查询，
在本地 PostgreSQL 数据库中执行，并将查询结果写入新列 GroundTruthValue。
"""

import os
import csv
import json
import sys
import psycopg2
from dotenv import load_dotenv

csv.field_size_limit(sys.maxsize)
load_dotenv()

# ---------- 数据库连接 ----------
HOST = os.getenv("PostgresSQLHost")
PORT = os.getenv("PostgresSQLPort")
DATABASE = os.getenv("PostgresSQLDBName")
USER = os.getenv("PostgresSQLUser")
PASSWORD = os.getenv("PostgresSQLPwd")
CONN_TIMEOUT = int(os.getenv("PostgresSQLConnTO", "30"))

CSV_INPUT = "Text2SQL_Test_Questions_Single_Value_RealData.csv"
CSV_OUTPUT = "Text2SQL_Test_Questions_Single_Value_RealData.csv"  # 写回原文件

SQL_COLUMN = "PostgreSQL_Query"
RESULT_COLUMN = "GroundTruthValue"


def connect_db():
    conn = psycopg2.connect(
        host=HOST,
        port=PORT,
        database=DATABASE,
        user=USER,
        password=PASSWORD,
        connect_timeout=CONN_TIMEOUT,
    )
    return conn


def execute_query(conn, sql_query: str) -> str:
    """执行一条 SQL，返回纯数值结果（单值查询直接返回数字）。"""
    try:
        with conn.cursor() as cur:
            cur.execute(sql_query)
            rows = cur.fetchall()

            # 单行单列 → 直接返回数值
            if len(rows) == 1 and len(rows[0]) == 1:
                val = rows[0][0]
                return str(val) if val is not None else "0"

            # 单行多列 → 逗号分隔
            if len(rows) == 1:
                return ", ".join(str(v) for v in rows[0])

            # 多行 → 每行一个值
            return "; ".join(", ".join(str(v) for v in row) for row in rows)
    except Exception as e:
        return f"ERROR: {e}"


def main():
    # 1) 读取 CSV
    with open(CSV_INPUT, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # 确保有结果列
    if RESULT_COLUMN not in fieldnames:
        fieldnames.append(RESULT_COLUMN)

    # 2) 连接数据库
    conn = connect_db()
    print(f"✅ 已连接到数据库 {DATABASE}@{HOST}:{PORT}")

    # 3) 逐行执行 SQL
    for i, row in enumerate(rows):
        sql_query = row.get(SQL_COLUMN, "").strip()
        row_id = row.get("ID", i + 1)

        if not sql_query:
            row[RESULT_COLUMN] = ""
            print(f"  [ID={row_id}] ⚠️  SQL 为空，跳过")
            continue

        print(f"  [ID={row_id}] 正在执行 SQL ...")
        result = execute_query(conn, sql_query)
        row[RESULT_COLUMN] = result

        # 打印简要摘要用于验证
        try:
            parsed = json.loads(result)
            if isinstance(parsed, list):
                print(f"           → 返回 {len(parsed)} 行")
            elif isinstance(parsed, dict) and "error" in parsed:
                print(f"           → ❌ 错误: {parsed['error']}")
        except Exception:
            pass

    conn.close()

    # 4) 写回 CSV
    with open(CSV_OUTPUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ 完成！结果已写入 {CSV_OUTPUT}（共 {len(rows)} 行）")

    # 5) 验证：抽查几行，打印 ID -> SQL 前 60 字符 + 结果前 100 字符
    print("\n===== 抽查验证 =====")
    for row in rows:
        row_id = row.get("ID", "?")
        sql_short = row.get(SQL_COLUMN, "")[:80]
        result_short = row.get(RESULT_COLUMN, "")[:120]
        print(f"  [ID={row_id}] SQL: {sql_short}")
        print(f"           Result: {result_short}")
        print()


if __name__ == "__main__":
    main()
