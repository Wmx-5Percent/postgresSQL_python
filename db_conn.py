import os
from dotenv import load_dotenv

import psycopg2
from psycopg2 import sql
from psycopg2 import OperationalError

load_dotenv()

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