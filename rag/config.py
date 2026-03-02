"""
RAG 配置文件
"""

import os

# base path
RAG_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(RAG_DIR, "knowledge")
CHROMA_PERSIST_DIR = os.path.join(RAG_DIR, "chroma_db")

# knowledge path
GOLDEN_SQLS_PATH = os.path.join(KNOWLEDGE_DIR, "golden_sqls.json")

# ChromaDB Collection name
COLLECTION_GOLDEN_SQLS = "golden_sqls"
COLLECTION_DDL = "ddl_statement"

# RAG recall setting for golden sqls
DEFAULT_TOP_K_GOLDEN_SQL = 3
DEFAULT_DISTANCE_THRESHOLD_GOLDEN_SQL = 0.5

# RAG recall setting for schemas
DEFAULT_TOP_K_SCHEMAS = 3
DEFAULT_DISTANCE_THRESHOLD_SCHEMAS = 0.8
