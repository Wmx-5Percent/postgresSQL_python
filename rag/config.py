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

# index para
DEFAULT_TOP_K = 3
DEFAULT_DISTANCE_THRESHOLD = 0.5