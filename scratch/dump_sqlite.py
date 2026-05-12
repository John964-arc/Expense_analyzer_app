import sqlite3
import json
import os

db_path = os.path.join('database', 'dev-data.sqlite')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

data = {}
tables = ['users', 'family_groups', 'family_members', 'expenses', 'budgets', 'savings_goals', 'savings_contributions']

for table in tables:
    try:
        cursor.execute(f"SELECT * FROM {table}")
        data[table] = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error reading {table}: {e}")
        data[table] = []

print(json.dumps(data))
conn.close()
