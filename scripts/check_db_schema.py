import sqlite3
import os

db_path = "samples/financial_data.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    for table in tables:
        if table[0] == 'financial_records':
            cursor.execute(f"PRAGMA table_info({table[0]})")
            cols = cursor.fetchall()
            print(f"--- Schema for {table[0]} ---")
            for col in cols:
                # Format: (id, name, type, notnull, default_value, pk)
                print(f"Col {col[0]}: {col[1]} ({col[2]})")
            cursor.execute(f"PRAGMA index_list({table[0]})")
            print(f"Indices: {cursor.fetchall()}")
    conn.close()
else:
    print(f"File {db_path} not found.")
