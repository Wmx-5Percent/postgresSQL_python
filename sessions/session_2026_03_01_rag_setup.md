# Session 记录：Text-to-SQL RAG 模块构建

**日期**：2026-03-01
**目标**：作为初学者，在现有的 Text-to-SQL Agent 中引入 RAG（ChromaDB），模拟 Vanna.ai 的架构

---

## 一、初始目标

基于现有的 Text-to-SQL 流水线（schema + 固定 few-shot prompt + LLM 两步生成 + 自动评估），引入 RAG 模块：
- 用 ChromaDB 作为向量数据库
- 把历史 Q&A 对存入向量库
- 用户提问时动态检索最相似的 few-shot 示例
- 注入到 prompt 中，替代/增强固定 few-shot

**改造前的流水线**：
```
用户问题 → 固定 SYSTEM_PROMPT(含固定few-shot) → LLM生成filters → LLM生成SQL → 执行SQL
```

**改造后的流水线**：
```
用户问题 → RAG检索相似Q&A → SYSTEM_PROMPT + 动态few-shot → LLM生成filters → LLM生成SQL → 执行SQL
```

---

## 二、已完成的步骤

### Step 1: `rag/config.py` ✅
- 定义了所有路径常量（`CHROMA_PERSIST_DIR`, `KNOWLEDGE_DIR`, `GOLDEN_SQLS_PATH`）
- 定义了检索参数（`DEFAULT_DISTANCE_THRESHOLD_GOLDEN_SQL=3`, `DEFAULT_DISTANCE_THRESHOLD=0.5`）
- 定义了 Collection 名称（`COLLECTION_GOLDEN_SQLS = "golden_sqls"`）

### Step 2: `rag/indexer.py` ✅
- `KnowledgeIndexer` 类，负责把 CSV 数据写入 ChromaDB
- `index_golden_sqls_from_csv(csv_path)` — 从测试 CSV 读取 30 条 Q&A
  - `Question_English` 列 → 作为 document 被向量化
  - `PostgreSQL_Query` 列 → 作为 metadata 原样存储
- `_upsert_to_collection(data)` — 核心写入方法
- `clear_all(collection_name)` — 删除指定 Collection
- 已成功运行，ChromaDB 中有 30 条数据

### Step 3: `rag/retriever.py` ✅
- `Text2SQLRetriver` 类，负责从 ChromaDB 检索相似 Q&A
- `retrieve(questions, top_k, distance_threshold)` — 支持单个/批量问题检索
  - 自动判断传入 str 还是 list[str]
  - 返回 `list[list[dict]]`，每个 dict 含 `question`, `distance`, `sql`
  - 用 `distance_threshold` 过滤不相关结果
- `build_rag_context(questions)` — 一键方法：检索 + 格式化成 prompt 文本
- 已成功运行，能检索到相关 Q&A 并返回对应的 SQL

### 当前文件夹结构
```
rag/
├── __init__.py              # 空文件
├── config.py                # 配置常量 ✅
├── indexer.py               # 索引器（写入 ChromaDB）✅
├── retriever.py             # 检索器（从 ChromaDB 检索）✅
├── build_index.py           # 暂未使用（indexer.py 已包含此功能）
├── chroma_db/               # ChromaDB 持久化数据（自动生成）✅
│   ├── chroma.sqlite3
│   └── d47fb920-.../
└── knowledge/
    └── .gitkeep
```

---

## 三、已完成的步骤（续）

### Step 4: 修改 `prompts/prompts.py` ✅
- 导入 `from rag.retriever import Text2SQLRetriver`
- 新增懒加载 `_get_retriever()` 函数，避免 import 时连接 ChromaDB
- 新增 `build_rag_enhanced_system_prompt(question)` — 检索相似 Q&A 并拼到 SYSTEM_PROMPT 后面
- 新增 `build_rag_enhanced_postgres_sql_generate_prompt(question, filters_json)` — 检索相似 Q&A 并拼到 SQL 生成 prompt 后面
- 在 `prompts/__init__.py` 中暴露了两个新函数

### Step 5: 修改 `evals/eval_runner.py` ✅
- 导入 `build_rag_enhanced_system_prompt` 和 `build_rag_enhanced_postgres_sql_generate_prompt`
- Step 1 (filters): `call_llm(client, model, build_rag_enhanced_system_prompt(question), question)`
- Step 2 (SQL): `call_llm(client, model, build_rag_enhanced_postgres_sql_generate_prompt(question, sql_filters), question)`
- 输出文件名改为 `eval_filter_with_RAG.csv`

### RAG 接入完成 ✅
至此，RAG 已完整接入 Text-to-SQL 流水线。完整数据流：
```
用户问题
  ↓
ChromaDB 检索最相似的 3 条 Q&A（retriever.retrieve）
  ↓
格式化成文本（retriever.build_rag_context）
  ↓
拼接到 SYSTEM_PROMPT 后面（build_rag_enhanced_system_prompt）
  ↓
LLM 生成 filters（call_llm）
  ↓
拼接到 SQL 生成 prompt 后面（build_rag_enhanced_postgres_sql_generate_prompt）
  ↓
LLM 生成 SQL（call_llm）
  ↓
执行 SQL → 比对 GroundTruth
```

---

## 四、待完成的步骤

### Step 6: 运行评估对比 ⬜
- 运行 eval_runner.py，生成 RAG 版本的评估结果
- 对比无 RAG vs 有 RAG 的准确率
- 注意：同一份数据做知识库和测试集 = 开卷考试，准确率会偏高

### Step 7: 收集独立的知识库数据 ⬜
- 把测试 CSV 拆分为训练集（知识库）和测试集
- 或收集更多真实 Q&A 对作为专门的知识库

### Step 8（优化）: 消除重复检索 ⬜
- 当前 eval_runner.py 中同一个问题被检索了 2 次（Step 1 和 Step 2 各一次）
- 优化：在 eval_runner.py 中只检索一次，把 rag_context 传下去复用

---

## 四、学到的知识点

### Python 基础
| 概念 | 要点 |
|------|------|
| `os.path` 系列 | `abspath`, `dirname`, `join`, `exists` 是最常用的 4 个 |
| `os.mkdir` vs `os.makedirs` | `makedirs` 可递归创建多层目录，更安全 |
| `from typing import List, Dict` | Python 3.9+ 可直接用 `list[dict]`，typing 是为兼容旧版本 |
| 类型注解 | 不影响运行，只是给 IDE 和人看的，类似 C 的类型声明 |
| `enumerate()` | 给循环加序号，`for i, item in enumerate(items, start=1)` |
| 模块导入路径 | `from config import` vs `from rag.config import`，取决于运行时的工作目录 |
| `sys.path.insert` | 手动把项目根目录加到 Python 搜索路径，解决跨模块导入问题 |
| `__init__.py` 中的 import | `from .module import` 中的 module 必须和实际文件名一致 |

### ChromaDB
| 概念 | 要点 |
|------|------|
| `Client()` vs `PersistentClient()` | 前者纯内存（测试用），后者存磁盘（正式用） |
| `Collection` | 类似数据库的表，一个 Collection 存一类数据 |
| `document` | 被向量化的文本（用于相似度匹配） |
| `metadata` | 附带信息，不参与向量化，检索到后原样返回 |
| `upsert` | update + insert，有就更新，没有就插入 |
| `query()` 返回结构 | 三层嵌套 `results["documents"][问题索引][结果索引]` |
| `query_texts` 支持批量 | 一次传多个问题比循环传单个更高效 |
| HNSW 算法 | 近似最近邻搜索，O(log n)，比暴力遍历快 |
| `delete_collection` | 只删逻辑记录，磁盘文件不一定立即清理 |
| 数据规模 | ChromaDB 适合 < 50 万条，更大用 Pinecone/Milvus |

### RAG 架构
| 概念 | 要点 |
|------|------|
| RAG 的作用 | 动态检索 few-shot 示例，替代固定 few-shot |
| `distance_threshold` | 防御性过滤，避免不相关结果误导 LLM |
| `top_k` | 控制返回数量 |
| 余弦距离 vs 相似度 | `similarity = 1 - distance`，距离越小越相似 |
| 知识库 vs 测试集 | 应该分开，否则是"开卷考试" |

---

## 五、代码改进建议

### 1. `indexer.py` — metadata 存储不够完整
**现状**：只存了 `PostgreSQL_Query`
**建议**：把 `Logic_Hint`, `Difficulty`, `Category` 也存进 metadata，检索后可以给 LLM 更多上下文

```python
# 当前
metadata = {}
if item.get("PostgreSQL_Query"):
    metadata["PostgreSQL_Query"] = item["PostgreSQL_Query"]

# 建议
metadata = {}
for key in ["PostgreSQL_Query", "Logic_Hint", "Difficulty", "Category"]:
    if item.get(key):
        metadata[key] = item[key]
```

### 2. `retriever.py` — 类名拼写
**现状**：`Text2SQLRetriver`（少了一个 e）
**建议**：改为 `Text2SQLRetriever`

### 3. `rag/__init__.py` — 当前是空的
**建议**：暴露核心接口，方便外部导入
```python
from rag.indexer import KnowledgeIndexer
from rag.retriever import Text2SQLRetriever
```

### 4. `indexer.py` — encoding 问题
**建议**：CSV 打开时用 `utf-8-sig` 避免 BOM 问题
```python
with open(csv_path, "r", encoding="utf-8-sig") as f:
```

### 5. 模块独立性
**现状**：`rag/` 模块不依赖 `evals/` 或 `prompts/`（正确）
**保持**：RAG 模块应该是独立的，只被其他模块调用，不反向依赖

---

## 六、后续可拓展的方向

1. **多路检索**：除了 golden_sqls，增加 column_descriptions、business_rules 的 Collection
2. **用 OpenAI Embedding**：替换 ChromaDB 默认的 all-MiniLM-L6-v2，用 text-embedding-3-small 效果更好
3. **知识库自动扩充**：eval 中正确的案例自动加回知识库
4. **排除自身**：eval 时排除当前问题本身，避免开卷考试效应
5. **测试拆分**：训练集 / 测试集分离，真实评估 RAG 效果
