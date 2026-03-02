"""临时脚本：查看 chroma.sqlite3 中存放的数据"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "rag", "chroma_db", "chroma.sqlite3")

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 列出所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    print("=" * 60)
    print(f"所有表 ({len(tables)}):")
    print("=" * 60)
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM [{t}]")
        count = cursor.fetchone()[0]
        print(f"  {t:40s}  ({count} 行)")

    # 2. 每张表的结构和前几行数据
    for t in tables:
        print("\n" + "=" * 60)
        print(f"表: {t}")
        print("=" * 60)

        # 表结构
        cursor.execute(f"PRAGMA table_info([{t}])")
        columns_info = cursor.fetchall()
        col_names = [c[1] for c in columns_info]
        print(f"列: {col_names}")

        # 前 10 行数据
        cursor.execute(f"SELECT * FROM [{t}] LIMIT 10")
        rows = cursor.fetchall()
        if not rows:
            print("  (空表)")
            continue

        for i, row in enumerate(rows):
            print(f"\n  --- 第 {i+1} 行 ---")
            for col_name, value in zip(col_names, row):
                display = value
                # 如果是很长的二进制或字符串，截断显示
                if isinstance(value, bytes):
                    display = f"<bytes, len={len(value)}>"
                elif isinstance(value, str) and len(value) > 200:
                    display = value[:200] + f"... (共 {len(value)} 字符)"
                print(f"    {col_name}: {display}")

    # 3. 尝试通过 ChromaDB 的 Python API 读取 collection 信息
    print("\n" + "=" * 60)
    print("通过 ChromaDB Python API 读取")
    print("=" * 60)
    try:
        import chromadb
        client = chromadb.PersistentClient(
            path=os.path.join(os.path.dirname(__file__), "rag", "chroma_db")
        )
        collections = client.list_collections()
        print(f"Collections 数量: {len(collections)}")
        for col in collections:
            print(f"\n  Collection: {col.name}  (id={col.id})")
            data = col.get(include=["documents", "metadatas"])
            ids = data["ids"]
            docs = data.get("documents", [])
            metas = data.get("metadatas", [])
            print(f"  文档数量: {len(ids)}")
            for j, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas)):
                doc_preview = doc[:150] + "..." if doc and len(doc) > 150 else doc
                print(f"\n    [{j+1}] id={doc_id}")
                print(f"        metadata={meta}")
                print(f"        document={doc_preview}")
    except ImportError:
        print("  chromadb 未安装，跳过 API 读取")
    except Exception as e:
        print(f"  ChromaDB API 读取失败: {e}")

    conn.close()

if __name__ == "__main__":
    main()
