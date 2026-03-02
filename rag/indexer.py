"""
索引器 - 把知识数据写入 ChromaDB

职责：读取 CSV/JSON → 写入 ChromaDB
只需要运行一次（或知识更新时重新运行）
"""

import os
import sys

# Dev-only: allow running this file interactively from evals/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json
import csv
from typing import List, Dict

import chromadb
import yaml

from rag.config import (
    CHROMA_PERSIST_DIR,
    KNOWLEDGE_DIR,
    GOLDEN_SQLS_PATH,
    COLLECTION_GOLDEN_SQLS,
    COLLECTION_DDL
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(BASE_DIR, "..", "tests", "Text2SQL_Test_Questions_Single_Value_RealData.csv")
yaml_path = os.path.join(BASE_DIR, "..", "schema_compact.yaml")  # 上级目录
# print(csv_path)

class KnowledgeIndexer:
    """
    知识索引器

    工作流程：
    1. 连接 ChromaDB（自动创建 chroma_db/ 目录）
    2. 读取数据源（CSV 或 JSON）
    3. 把 question 作为 document（会被向量化）
    4. 把 sql、logic_hint 等作为 metadata（原样存储，检索到后一起返回）
    5. 写入 ChromaDB
    """

    def __init__(self, persist_directory: str = CHROMA_PERSIST_DIR) -> None:
        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)
        print(f"ChromaDB initializing at: {persist_directory}")
    
    def index_golden_sqls_from_csv(self, csv_path: str) -> None:
        """
        从测试 CSV 构建 golden_sqls 索引

        CSV 必须包含这些列：
        - ID
        - Question_English    → 会被向量化（document）
        - PostgreSQL_Query    → 作为 metadata 存储
        - Logic_Hint          → 作为 metadata 存储
        - Difficulty          → 作为 metadata 存储
        - Category            → 作为 metadata 存储
        """
        examples = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                examples.append(row)
        print(f"Read {len(examples)} rows from {csv_path}")

        self._upsert_to_collection(examples)

    def _upsert_to_collection(self, data: List[Dict]) -> None:
        collection = self.client.get_or_create_collection(
            name=COLLECTION_GOLDEN_SQLS,
            metadata={"hnsw:space": "cosine"},
        )
        documents = []
        metadatas = []
        ids = []

        for item in data:
            documents.append(item["Question_English"])

            metadata = {}
            if item.get("PostgreSQL_Query"):
                metadata["PostgreSQL_Query"] = item["PostgreSQL_Query"]
            metadatas.append(metadata)            
            ids.append(item["ID"])
        
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        print(f"Upserted {len(documents)} documents → collection '{COLLECTION_GOLDEN_SQLS}' "
              f"(total: {collection.count()})")
    
    def index_table_schema(self, yaml_file_path: str) -> None:
        with open(yaml_file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        
        table = yaml_data['tables'][0]
        columns = table['columns']

        fields_info = ", ".join(
            f"{col['name']}: {col.get('description', '')}"
            for col in columns
        )
              
        yaml_document = (
            f"table_name: {table['table_name']}. "
            f"table_description: {table['description']}. "
            f"columns: {fields_info}."
        )

        yaml_metadata = {
            "table_name": table["table_name"],
            "table_description": table["description"],
            "ddl_yaml": yaml.dump(table, default_flow_style=False, allow_unicode=True),
        }

        self._upsert_table_schema_collection(
            ids=table["table_name"],
            document=yaml_document,
            metadata=yaml_metadata
        )
    
    
    def _upsert_table_schema_collection(self, ids: str, document: str, metadata: Dict) -> None:
        collection = self.client.get_or_create_collection(
            name=COLLECTION_DDL,
            metadata={"hnsw:space": "cosine"}
        )

        collection.upsert(
            ids=ids,
            documents=document,
            metadatas=metadata,
        )

    def clear_all(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(collection_name)
            print(f"Deleted collection: {collection_name}")
        except Exception as e:
            print(f"Collection '{collection_name}' delete failed:", e)



if __name__ == "__main__":
    knowledgeIndexer = KnowledgeIndexer()
    knowledgeIndexer.index_table_schema(yaml_path)
    knowledgeIndexer.index_golden_sqls_from_csv(csv_path)
