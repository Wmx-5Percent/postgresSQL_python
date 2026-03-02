# Session 记录：DDL 向量库构建

**日期**：2026-03-03  
**目标**：在现有 Golden SQL 向量库基础上，新增 DDL（表结构）向量库，向 Vanna.ai 三路检索架构迈进

---

## 一、背景 & 目标

Vanna.ai 的 RAG 架构包含三个向量库：

```
用户问题
  ├─→ ① Golden SQL 向量库    → 检索相似的 Q&A 示例         ✅ Session 03-01 已完成
  ├─→ ② DDL 向量库           → 检索相关表的结构信息         ← 本次 Session
  └─→ ③ 业务文档向量库        → 检索业务规则/约定            ⬜ 下一步
```

本次目标：构建 DDL 向量库，让 RAG 能根据用户问题检索到相关的表结构（表名、列名、列描述），注入 prompt 辅助 LLM 生成更准确的 SQL。

---

## 二、设计决策

### 2.1 存储格式：YAML

选择 YAML 作为 schema 的存储格式（而非 JSON），原因：
- 人类可读性更好，方便手动编辑和维护
- 支持多行描述（`description: >`）
- 未来新增表时只需创建新的 YAML 文件

已有文件：`schema_compact.yaml`，包含一张表 `t_mr_cs_summary_dailyFourSysResult` 的完整结构。

### 2.2 存入向量库的数据结构

**核心矛盾**：向量检索需要简明扼要的自然语言，而 LLM 生成 SQL 需要事无巨细的结构信息。

**解决方案**：分离 document 和 metadata

| 字段 | 内容 | 用途 |
|------|------|------|
| `id` | 表名（如 `t_mr_cs_summary_dailyFourSysResult`） | 唯一标识，upsert 时自动更新 |
| `document` | 表名 + 表描述 + 列名:列描述（纯文本，无换行） | 被向量化，用于相似度检索 |
| `metadata.table_name` | 表名 | 检索后返回给 LLM |
| `metadata.table_description` | 表的用途描述 | 检索后返回给 LLM |
| `metadata.ddl_yaml` | 完整 YAML 序列化成字符串 | 检索后返回给 LLM，包含所有细节 |

**为什么 metadata 存 YAML 字符串而不是嵌套 dict？**  
→ ChromaDB metadata 只支持扁平的 `str / int / float / bool`，不支持嵌套结构。用 `yaml.dump()` 序列化成字符串存储。

### 2.3 document 设计

```
table_name: t_mr_cs_summary_dailyFourSysResult. table_description: Summary view of daily CS notifications... columns: NOTI_ID: Unique notification identifier, NOTI_DT: Notification creation date, NOTI_COUNTRY_TEXT: Full country name...
```

- 纯文本，无换行、无缩进、无 YAML 符号
- 包含列名 + 列描述，作为"语义锚点"（用户说"德国"能匹配到 `NOTI_COUNTRY_TEXT: Full country name`）
- 当前只有 1 张表时列描述意义不大，但为多表扩展预留

### 2.4 粒度：按表存储

一张表 = 一条记录，不按字段拆分。原因：
- 按字段拆分后，检索只命中 1-2 个字段，LLM 看不到完整表结构
- 按表存储，检索到后 LLM 直接拿到完整 DDL

---

## 三、已完成的步骤

### Step 1: `rag/config.py` 更新 ✅

新增 DDL 向量库相关配置：

```python
# ChromaDB Collection name
COLLECTION_DDL = "ddl_statement"

# RAG recall setting for schemas
DEFAULT_TOP_K_SCHEMAS = 3
DEFAULT_DISTANCE_THRESHOLD_SCHEMAS = 0.8  # DDL 匹配可以宽松一些，表数量少
```

同时重命名了 Golden SQL 的配置变量，使命名更清晰：
- `DEFAULT_TOP_K` → `DEFAULT_TOP_K_GOLDEN_SQL`
- `DEFAULT_DISTANCE_THRESHOLD` → `DEFAULT_DISTANCE_THRESHOLD_GOLDEN_SQL`

### Step 2: `rag/indexer.py` 新增 DDL 索引方法 ✅

新增两个方法：

- `index_table_schema(yaml_file_path)` — 解析 YAML → 构建 document + metadata → 写入 ChromaDB
  - 用 `yaml.safe_load()` 解析 YAML 为 Python dict
  - 用 `", ".join()` 将列信息拼成纯文本 `fields_info`
  - 用 `yaml.dump()` 将完整表结构序列化成字符串存入 metadata
- `_upsert_table_schema_collection(ids, document, metadata)` — 写入 `ddl_statement` Collection

### Step 3: `rag/retriever.py` 新增 schema 检索方法骨架 ✅（未完成）

新增了 `schemas_retriever()` 方法签名，但方法体尚未实现。

### Step 4: `schema_compact.yaml` 已就绪 ✅

已有完整的 YAML schema 文件，包含：
- 表名、表描述、主键
- 22 个字段的 name、type、description
- 枚举值（如 `NOTI_SP_CONSUMED_FLG` 的 Y/N）

---

## 四、待完成的步骤

### Step 5: 完成 `schemas_retriever()` 方法 ⬜

```python
def schemas_retriever(self, questions, top_k, distance_threshold) -> List[List[Dict]]:
    # 从 ddl_statement Collection 检索相关表的 DDL
    # 返回 table_name, table_description, ddl_yaml
```

### Step 6: 新增 `build_ddl_context()` 方法 ⬜

类似 `build_rag_context()`，将检索到的 DDL 信息格式化成可注入 prompt 的文本：

```python
def build_ddl_context(self, questions) -> str:
    # 检索 + 格式化
    # 输出示例：
    # === Relevant Table Schemas ===
    # Table: t_mr_cs_summary_dailyFourSysResult
    # Description: ...
    # Columns: ...
```

### Step 7: 将 DDL Context 接入 prompt ⬜

在 `prompts/prompts.py` 中将 DDL context 注入到 SQL 生成 prompt：

```
SYSTEM_PROMPT
  + DDL Context (从 schemas_retriever 获取)    ← 告诉 LLM 有哪些表和字段
  + RAG Context (从 retrieve 获取)              ← 告诉 LLM 相似问题的 SQL 写法
  + 用户问题
  → LLM 生成 SQL
```

### Step 8: 验证 & 评估 ⬜

- 运行 `indexer.py` 确认 DDL 数据成功写入 ChromaDB
- 运行 `tmp_inspect_chroma.py` 检查 `ddl_statement` Collection 内容
- 运行评估对比接入 DDL Context 前后的 SQL 生成准确率

---

## 五、当前文件结构

```
rag/
├── __init__.py
├── config.py                # 通用配置（含 DDL 配置）     ✅ 已更新
├── indexer.py               # 索引器（Golden SQL + DDL）  ✅ 已更新
├── retriever.py             # 检索器（DDL 检索待完成）     🔨 部分完成
├── chroma_db/               # ChromaDB 持久化数据
│   ├── chroma.sqlite3
│   └── .../
└── knowledge/
```

---

## 六、学到的知识点

### YAML 解析
| 概念 | 要点 |
|------|------|
| `yaml.safe_load(f)` | YAML → Python dict，跟 `json.load(f)` 用法一样 |
| `yaml.dump(dict)` | Python dict → YAML 字符串，用于存入 metadata |
| `yaml.SafeLoader` | 底层类，不直接使用，用 `safe_load()` 函数即可 |
| 安装 | `pip install pyyaml`，import 时用 `import yaml` |

### ChromaDB metadata 限制
| 概念 | 要点 |
|------|------|
| 支持的类型 | `str`, `int`, `float`, `bool` 仅此四种 |
| 不支持嵌套 | `{"columns": [{"name": "..."}]}` 会报错 |
| 解决方案 | 用 `yaml.dump()` 或 `json.dumps()` 序列化成字符串 |

### 向量库设计原则
| 概念 | 要点 |
|------|------|
| document vs metadata | document 用于检索匹配（会被向量化），metadata 用于信息传递（原样返回） |
| document 应是自然语言 | 结构化文本（YAML/JSON/DDL）不适合直接向量化 |
| 语义锚点 | document 中需要包含用户可能使用的关键词（如国家名、产品名） |
| 存储粒度 | 按表存，不按字段拆分 |
| ids 的作用 | 唯一标识 + 支持 upsert 更新 |
