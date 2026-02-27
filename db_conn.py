import os
from dotenv import load_dotenv

import psycopg2
from psycopg2 import sql
from psycopg2 import OperationalError

import sqlite3

load_dotenv()

# %%
def query_data_base(sql_query: str) -> dict:
    """
    执行 SQL 查询，返回列名和所有行数据。
    
    Returns:
        {
            "columns": ["col1", "col2", ...],
            "rows": [(val1, val2, ...), ...],
            "row_count": int
        }
        如果出错，返回 {"error": "错误信息"}
    """
    try:
        conn = sqlite3.connect("local_database.db")
        cursor = conn.cursor()
        cursor.execute(sql_query)

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        conn.close()

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows)
        }
    except Exception as e:
        print("sql query error:", e)

SQL = f"""
step2: SQL =====
SELECT
  NOTI_ID,
  NOTI_ASSIGNED_DT,
  NOTI_CATEGORY_TEXT,
  MAT_IVK_GROUP_TEXT,
  Problem_CAT_L1_LLM,
  Problem_CAT_L2_LLM,
  Issue_Summary_LLM,
  Troubleshooting_Steps_LLM,
  Solution_And_Action_Taken_LLM,
  NOTI_COUNTRY_ID,
  NOTI_CURRENT_CLOSED_DT
FROM t_mr_cs_summary_dailyFourSysResult
WHERE SYS_MAT_ID = '11060815'
  AND SYS_SERIAL_ID = '175678'
ORDER BY NOTI_ASSIGNED_DT DESC NULLS LAST
LIMIT 100;
"""
query_results = query_data_base(SQL)
print(query_results)

if __name__ == "__main__":
    HOST=os.getenv("PostgresSQLHost")
    PORT=os.getenv("PostgresSQLPort")
    DATABASE=os.getenv("PostgresSQLDBName")
    USER=os.getenv("PostgresSQLUser")
    PASSWORD=os.getenv("PostgresSQLPwd")
    CONN_TIMEOUT=30

    print("Host:", os.getenv("PostgresSQLHost"))
    print("Port:", os.getenv("PostgresSQLPort"))
    print("Database:", os.getenv("PostgresSQLDBName"))
    print("User:", os.getenv("PostgresSQLUser"))
    print("Password:", os.getenv("PostgresSQLPwd"))

    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USER,
            password=PASSWORD,
            connect_timeout=CONN_TIMEOUT
        )
        print(f"Database connection successful!")
    except OperationalError as e:
        print("Error connecting to the database:", e)


    test_sql = f"""
    SELECT COUNT(DISTINCT NOTI_ID) AS NOTI_ID_CNT
    FROM public.t_mr_cs_summary_dailyfourSysresult AS vcs
    """

    with conn.cursor() as cur:
        cur.execute(test_sql)
        print(cur.fetchone())

    conn.close()

    from sqlalchemy import create_engine, text

    try: 
        engine = create_engine(
            f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}",
            pool_pre_ping=True,
        )
        with engine.connect() as connection:
            result = connection.execute(text(test_sql))
            print("result:", result.fetchone())
        print(f"connect DB with sqlalchemy successful!")
    except OperationalError as e:
        print("Error connecting DB with sqlalchemy:", e)

    # %%
    import sqlite3

    # %%
    # 连接（就这一行，不需要用户名密码端口什么的）
    conn = sqlite3.connect("local_database.db")
    cursor = conn.cursor()

    # 查询（带列名）
    cursor.execute("SELECT * FROM t_mr_cs_summary_dailyfoursysresult LIMIT 10")
    columns = [desc[0] for desc in cursor.description]  # 获取列名
    rows = cursor.fetchall()

    print(type(cursor.description))
    print(cursor.description)

    print("列名:", columns)
    print("-" * 80)
    for row in rows:
        for col, val in zip(columns, row):
            print(f"  {col}: {val}")
        print("-" * 80)

    conn.close()