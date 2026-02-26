# PostgreSQL + LLM SQL Generator

利用 OpenAI LLM 将自然语言转换为 PostgreSQL 查询语句的两阶段 pipeline：

1. **Step 1** — 用户问题 → LLM 提取 SQL Filters（JSON）
2. **Step 2** — Filters JSON + 用户问题 → LLM 生成可执行的 PostgreSQL SELECT 语句

目标数据库表：`public.t_mr_cs_summary_dailyfourSysresult`（Service Ticket 数据）

---

## 项目结构

```
├── chat_with_openai.py      # 主程序：两阶段 LLM 调用
├── prompts.py               # System Prompt 定义 + SQL 生成 Prompt 构建函数
├── db_conn.py               # 数据库连接测试（psycopg2 + SQLAlchemy）
├── schema_compact.yaml      # 数据库 schema（列白名单，注入 prompt）
├── schema_output.json       # Schema 输出参考
├── db_dump.sql              # 数据库完整快照（schema + data，约 3MB）
├── docker-compose.yml       # 一键启动 PostgreSQL 容器
├── .env.example             # 环境变量模板
├── requirements.txt         # Python 依赖
└── .gitignore
```

---

## 快速开始（新主机）

### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 已安装
- Python 3.10+
- OpenAI API Key

### 1. 克隆项目

```bash
git clone git@github.com:Wmx-5Percent/postgresSQL_python.git
cd postgresSQL_python
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入真实值：

```dotenv
# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# PostgreSQL（与 docker-compose 对应，可直接使用以下默认值）
PostgresSQLHost=localhost
PostgresSQLPort=5432
PostgresSQLDBName=SSMR_DW
PostgresSQLUser=postgres
PostgresSQLPwd=your_password    # ← 设置你的密码
```

### 3. 一键启动数据库（Docker）

```bash
docker compose up -d
```

> **首次启动**会自动执行 `db_dump.sql`，将所有表结构和数据导入 PostgreSQL 容器。
> 后续重启不会重复导入（数据持久化在 Docker volume 中）。

验证数据库是否就绪：

```bash
docker exec -it postgresSQL_python_db psql -U postgres -d SSMR_DW -c "SELECT COUNT(*) FROM public.t_mr_cs_summary_dailyfourSysresult;"
```

### 4. Python 环境

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 5. 运行

```bash
# 测试数据库连接
python db_conn.py

# 运行 LLM SQL 生成 pipeline
python chat_with_openai.py
```

---

## 开发指南

### 两阶段 Pipeline 流程

```
用户自然语言问题
       │
       ▼
┌─────────────────────────┐
│ Stage 1: Filter 提取     │  SYSTEM_PROMPT（prompts.py）
│ 输出: SQL Filters JSON   │
└───────────┬─────────────┘
            │
            ▼  filters_json 动态注入
┌─────────────────────────┐
│ Stage 2: SQL 生成        │  build_sql_generate_prompt(filters_json)
│ 输出: PostgreSQL SELECT  │
└─────────────────────────┘
```

### 修改 Schema

编辑 `schema_compact.yaml` 添加/修改列定义，程序启动时自动加载并注入到 prompt 中。

### 修改 Prompt

编辑 `prompts.py`：
- `SYSTEM_PROMPT` — 控制 Stage 1（Filter 提取）行为
- `build_sql_generate_prompt()` — 控制 Stage 2（SQL 生成）行为

---

## 常见问题

### Docker 容器启动后数据库是空的？

确认 `db_dump.sql` 存在于项目根目录。如果容器之前已启动过，需要清除 volume 重新导入：

```bash
docker compose down -v    # 删除旧 volume
docker compose up -d      # 重新创建并导入
```

### 端口 5432 被占用？

修改 `.env` 中的 `PostgresSQLPort`（如改为 `5433`），Docker Compose 会自动映射。

### 如何更新数据库快照？

在有最新数据的机器上重新导出：

```bash
pg_dump -h localhost -U postgres -d SSMR_DW -F p -f db_dump.sql
git add db_dump.sql && git commit -m "update db dump" && git push
```
