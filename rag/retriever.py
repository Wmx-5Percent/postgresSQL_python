"""
检索器 - 从 ChromaDB 检索相关知识

职责：接收用户问题 → 从 ChromaDB 检索最相似的 Q&A → 返回结构化结果
每次用户提问时调用
"""

import os
import sys

# Dev-only: allow running this file interactively from evals/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from typing import List, Dict

import chromadb

from rag.config import (
    CHROMA_PERSIST_DIR,
    DEFAULT_DISTANCE_THRESHOLD,
    DEFAULT_TOP_K,
    COLLECTION_GOLDEN_SQLS
)

class Text2SQLRetriver:
    """
    Text-to-SQL 检索器

    工作流程：
    1. 连接已有的 ChromaDB（indexer 已经写入过数据）
    2. 接收用户问题
    3. ChromaDB 自动把问题向量化 → 和库里的向量做余弦相似度
    4. 返回最相似的 N 条 Q&A（包含 question + metadata）
    """
    def __init__(self, persist_directory: str = CHROMA_PERSIST_DIR) -> None:
        self.client = chromadb.PersistentClient(persist_directory)
    
    def retrieve(
            self,
            questions: List[str],
            top_k: int = DEFAULT_TOP_K,
            distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD
    ) -> List[List[Dict]]:
        """
        检索最相似的 Q&A

        参数：
            question: 用户的新问题
            top_k: 返回几条最相似的结果
            distance_threshold: 余弦距离阈值，超过的丢弃（越小越相似）

        返回：
            [
                {
                    "question": "How many tickets for AMIRA in Germany?",
                    "sql": "SELECT COUNT(DISTINCT NOTI_ID)...",
                    "distance": 0.15
                },
                ...
            ]
        """
        try: 
            collection = self.client.get_collection(COLLECTION_GOLDEN_SQLS)
        except Exception as e:
            print("Get ChromaDB collection failed: ", e)
            return [[] for _ in questions]
        
        if collection.count() == 0:
            print("Collection is empty. Run indexer first.")
            return [[] for _ in questions]
        
        results = collection.query(
            query_texts=questions,
            n_results=min(top_k, collection.count())
        )

        all_retrieved = []
        for q_idx in range(len(questions)):
            retrieved = []
            for i in range(len(results["documents"][q_idx])):
                distance = results["distances"][q_idx][i]

                if distance > distance_threshold:
                    continue

                item = {
                    "question": results["documents"][q_idx][i],
                    "distance": distance,
                }

                metadata = results["metadatas"][q_idx][i]
                if metadata:
                    if "PostgreSQL_Query" in metadata:
                        item["sql"] = metadata["PostgreSQL_Query"]
                
                retrieved.append(item)
            all_retrieved.append(retrieved)
        return all_retrieved

    def build_rag_context(self, questions: List[str]) -> str:
        results = self.retrieve(questions)

        if not results:
            return ""
        
        lines = ["## Few-Shot Examples"]
        lines.append("\n--- RAG Retrieved Context (use these as reference examples) ---")

        example_count = 1
        for cases in results:
            for res in cases:
                similarity = 1 - float(res['distance'])
                lines.append(f"\nExample {example_count} (similarity: {similarity:.2f}):")
                lines.append(f" Question: {res['question']}")
                if "sql" in res:
                    lines.append(f" SQL: {res['sql']}")
                if "logic_hint" in res:
                    lines.append(f" Logic: {res['logic_hint']}")
                example_count += 1
            
        lines.append("\n--- End of RAG Context ---")

        return "\n".join(lines)


if __name__ == "__main__":
    retriever = Text2SQLRetriver()

    test_question_1 = "What is the total count of service requests assigned in the month of February 2025?"
    test_question_2 = "Who are the top 3 field service engineers with the fastest average resolution time for AMIRA systems?"
    # retrieved = retriever.retrieve([test_question_1], distance_threshold=0.3)
    # for q_idx, items in enumerate(retrieved, 1):
    #     print(f"\n{'='*60}")
    #     print(f"Question {q_idx}")
    #     print(f"Found {len(items)} results:")
    #     print(f"{'='*60}")
    #     for rank, q in enumerate(items, 1):
    #         print(f"  #{rank} | distance: {q['distance']:.4f} | {q['question']}")
    #         if "sql" in q:
    #              print(f"         SQL: {q['sql']}")
    
    print("\n" + retriever.build_rag_context([test_question_1]))
