"""验证脚本：抽查 CSV 中的 GroundTruthValue 是否与数据库查询结果一致。"""

import csv
import json
import os
import sys
import psycopg2
from dotenv import load_dotenv

csv.field_size_limit(sys.maxsize)
load_dotenv()

# 读取 CSV
with open("Text2SQL_Test_Questions_Single_Value_RealData.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# 连接数据库
conn = psycopg2.connect(
    host=os.getenv("PostgresSQLHost"),
    port=os.getenv("PostgresSQLPort"),
    database=os.getenv("PostgresSQLDBName"),
    user=os.getenv("PostgresSQLUser"),
    password=os.getenv("PostgresSQLPwd"),
    connect_timeout=5,
)

check_ids = list(range(1, 31))  # 验证全部 30 条
all_pass = True

for row in rows:
    rid = int(row["ID"])
    if rid not in check_ids:
        continue
    sql = row["PostgreSQL_Query"]
    gt = row["GroundTruthValue"]

    with conn.cursor() as cur:
        cur.execute(sql)
        db_rows = cur.fetchall()

        if len(db_rows) == 1 and len(db_rows[0]) == 1:
            val = db_rows[0][0]
            fresh = str(val) if val is not None else "0"
        elif len(db_rows) == 1:
            fresh = ", ".join(str(v) for v in db_rows[0])
        else:
            fresh = "; ".join(", ".join(str(v) for v in row) for row in db_rows)
    match = fresh == gt
    status = "MATCH" if match else "MISMATCH"
    print(f"ID={rid}: {status}")
    if not match:
        all_pass = False
        print(f"  CSV:   {gt[:200]}")
        print(f"  Fresh: {fresh[:200]}")

conn.close()
print()
print("Overall:", "ALL PASSED" if all_pass else "SOME FAILED")
