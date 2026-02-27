"""
convert_to_sqlite.py
将 PostgreSQL dump 转换并导入 SQLite
"""
# %%
import sqlite3
import re
import os
import csv
import io

# ============ 配置 ============
SQL_DUMP_FILE = "db_dump.sql"
SQLITE_DB_FILE = "local_database.db"
# ==============================


def parse_pg_dump(sql_content: str):
    """解析 PostgreSQL dump 文件，返回 CREATE TABLE 语句和 COPY 数据"""
    
    results = {
        'create_tables': [],  # (table_name, create_sql)
        'copy_data': [],      # (table_name, columns, rows)
    }
    
    lines = sql_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # ---- 解析 CREATE TABLE ----
        if line.upper().startswith('CREATE TABLE'):
            create_lines = []
            while i < len(lines):
                create_lines.append(lines[i])
                if lines[i].strip().endswith(';'):
                    break
                i += 1
            
            create_sql = '\n'.join(create_lines)
            
            # 提取表名
            match = re.search(r'CREATE TABLE\s+(?:public\.)?(\S+)', create_sql, re.IGNORECASE)
            if match:
                table_name = match.group(1).strip('"')
                
                # 转换 PostgreSQL 类型为 SQLite 类型
                sqlite_sql = pg_create_to_sqlite(create_sql)
                results['create_tables'].append((table_name, sqlite_sql))
        
        # ---- 解析 COPY ... FROM stdin ----
        elif line.upper().startswith('COPY '):
            match = re.match(
                r'COPY\s+(?:public\.)?(\S+)\s*\(([^)]+)\)\s+FROM\s+stdin',
                line, re.IGNORECASE
            )
            if match:
                table_name = match.group(1).strip('"')
                columns = [c.strip().strip('"') for c in match.group(2).split(',')]
                
                # 读取数据行（直到遇到 \. 结束标记）
                data_rows = []
                i += 1
                while i < len(lines):
                    data_line = lines[i]
                    if data_line.strip() == '\\.':
                        break
                    # PostgreSQL COPY 用 Tab 分隔
                    # \N 表示 NULL
                    fields = data_line.split('\t')
                    fields = [None if f == '\\N' else f for f in fields]
                    data_rows.append(fields)
                    i += 1
                
                results['copy_data'].append((table_name, columns, data_rows))
        
        i += 1
    
    return results


def pg_create_to_sqlite(create_sql: str) -> str:
    """将 PostgreSQL CREATE TABLE 转换为 SQLite 兼容语法"""
    
    # 移除 schema 前缀
    create_sql = create_sql.replace('public.', '')
    
    # PostgreSQL 类型 -> SQLite 类型
    type_map = [
        (r'character varying\(\d+\)', 'TEXT'),
        (r'character varying', 'TEXT'),
        (r'varchar\(\d+\)', 'TEXT'),
        (r'varchar', 'TEXT'),
        (r'\bcharacter\(\d+\)', 'TEXT'),
        (r'\bchar\(\d+\)', 'TEXT'),
        (r'\btext\b', 'TEXT'),
        (r'\buuid\b', 'TEXT'),
        (r'\bjsonb\b', 'TEXT'),
        (r'\bjson\b', 'TEXT'),
        (r'\btimestamp without time zone\b', 'TEXT'),
        (r'\btimestamp with time zone\b', 'TEXT'),
        (r'\btimestamp\b', 'TEXT'),
        (r'\bdate\b', 'TEXT'),
        (r'\btime without time zone\b', 'TEXT'),
        (r'\btime with time zone\b', 'TEXT'),
        (r'\bboolean\b', 'INTEGER'),
        (r'\bbigint\b', 'INTEGER'),
        (r'\binteger\b', 'INTEGER'),
        (r'\bsmallint\b', 'INTEGER'),
        (r'\bbigserial\b', 'INTEGER'),
        (r'\bserial\b', 'INTEGER'),
        (r'\bdouble precision\b', 'REAL'),
        (r'\bnumeric\(\d+,\d+\)', 'REAL'),
        (r'\bnumeric\b', 'REAL'),
        (r'\breal\b', 'REAL'),
        (r'\bbytea\b', 'BLOB'),
    ]
    
    for pg_type, sqlite_type in type_map:
        create_sql = re.sub(pg_type, sqlite_type, create_sql, flags=re.IGNORECASE)
    
    # 移除 PostgreSQL 特有的约束语法
    create_sql = re.sub(r'DEFAULT\s+nextval\([^)]+\)', '', create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'DEFAULT\s+now\(\)', "DEFAULT ''", create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'DEFAULT\s+CURRENT_TIMESTAMP', "DEFAULT ''", create_sql, flags=re.IGNORECASE)
    create_sql = re.sub(r'::[\w\s]+', '', create_sql)  # 移除类型转换 ::type
    
    # 修复可能多出的逗号
    create_sql = re.sub(r',\s*\)', ')', create_sql)
    
    return create_sql


def import_to_sqlite():
    """主函数：读取 PostgreSQL dump 并导入 SQLite"""
    
    if not os.path.exists(SQL_DUMP_FILE):
        print(f"❌ 找不到文件: {SQL_DUMP_FILE}")
        return
    
    # 如果数据库已存在，尝试删除；如果被占用则清空表
    if os.path.exists(SQLITE_DB_FILE):
        try:
            os.remove(SQLITE_DB_FILE)
            print(f"🗑️  已删除旧数据库: {SQLITE_DB_FILE}")
        except PermissionError:
            print(f"⚠️  文件被占用，将清空已有表后重新导入...")
    
    # 读取 SQL 文件
    print(f"📖 读取 {SQL_DUMP_FILE}...")
    with open(SQL_DUMP_FILE, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 解析 PostgreSQL dump
    print("🔄 解析 PostgreSQL dump...")
    parsed = parse_pg_dump(sql_content)
    
    print(f"   找到 {len(parsed['create_tables'])} 个 CREATE TABLE")
    print(f"   找到 {len(parsed['copy_data'])} 个 COPY 数据块")
    
    # 连接 SQLite 并执行
    conn = sqlite3.connect(SQLITE_DB_FILE)
    
    # 如果文件无法删除，先清空已有的表
    if os.path.exists(SQLITE_DB_FILE):
        cursor_clean = conn.cursor()
        cursor_clean.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for (tbl,) in cursor_clean.fetchall():
            cursor_clean.execute(f'DROP TABLE IF EXISTS "{tbl}"')
        conn.commit()
    cursor = conn.cursor()
    
    # 1. 创建表
    create_count = 0
    for table_name, create_sql in parsed['create_tables']:
        try:
            cursor.execute(create_sql)
            create_count += 1
            print(f"   ✅ 创建表: {table_name}")
        except Exception as e:
            print(f"   ❌ 创建表 {table_name} 失败: {e}")
            print(f"      SQL: {create_sql[:200]}...")
    
    # 2. 插入数据
    insert_count = 0
    error_count = 0
    for table_name, columns, rows in parsed['copy_data']:
        if not rows:
            print(f"   ⚠️  表 {table_name} 没有数据")
            continue
        
        placeholders = ','.join(['?' for _ in columns])
        col_names = ','.join([f'"{c}"' for c in columns])
        insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
        
        for row_idx, row in enumerate(rows):
            try:
                # 确保字段数量匹配
                if len(row) != len(columns):
                    print(f"   ⚠️  表 {table_name} 第 {row_idx+1} 行字段数不匹配: "
                          f"期望 {len(columns)}, 实际 {len(row)}")
                    error_count += 1
                    continue
                
                cursor.execute(insert_sql, row)
                insert_count += 1
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # 只打印前5个错误
                    print(f"   ❌ 插入 {table_name} 第 {row_idx+1} 行失败: {e}")
    
    conn.commit()
    
    # 打印结果摘要
    print("\n" + "=" * 50)
    print("📊 导入结果:")
    print(f"   ✅ 创建表: {create_count} 个")
    print(f"   ✅ 插入行: {insert_count} 行")
    print(f"   ❌ 失败: {error_count} 行")
    print("=" * 50)
    
    # 显示所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print(f"\n📋 数据库中的表 ({len(tables)} 个):")
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM "{table[0]}"')
        count = cursor.fetchone()[0]
        print(f"   📁 {table[0]}: {count} 条记录")
    
    conn.close()
    print(f"\n✅ 数据库已保存到: {SQLITE_DB_FILE}")
    print(f"   文件大小: {os.path.getsize(SQLITE_DB_FILE) / 1024:.1f} KB")


# %%
if __name__ == "__main__":
    import_to_sqlite()