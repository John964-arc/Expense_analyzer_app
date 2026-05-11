import os
import sys
from sqlalchemy import create_engine, MetaData, select
from sqlalchemy.orm import sessionmaker

# Ensure the app context is available if needed, or just use raw SQLAlchemy
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    sqlite_url = 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), 'database', 'dev-data.sqlite'))
    # Load from config or .env.local
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env.local'))
    
    postgres_url = os.environ.get('DATABASE_URL')
    if not postgres_url:
        print("DATABASE_URL not found in .env.local")
        return

    print(f"Connecting to SQLite: {sqlite_url}")
    sqlite_engine = create_engine(sqlite_url)
    
    print(f"Connecting to Postgres: {postgres_url}")
    pg_engine = create_engine(postgres_url)

    # Reflect schemas
    meta_sqlite = MetaData()
    meta_sqlite.reflect(bind=sqlite_engine)
    
    meta_pg = MetaData()
    meta_pg.reflect(bind=pg_engine)

    # Order of tables to migrate (respecting foreign keys)
    # Users first, then FamilyGroups, then FamilyMembers, Budgets, SavingsGoals, SavingsContributions, Expenses
    tables_to_migrate = [
        'users',
        'family_groups',
        'family_members',
        'budgets',
        'savings_goals',
        'savings_contributions',
        'expenses'
    ]

    sqlite_conn = sqlite_engine.connect()
    pg_conn = pg_engine.connect()
    
    for table_name in tables_to_migrate:
        if table_name not in meta_sqlite.tables:
            print(f"Skipping {table_name}: not found in SQLite.")
            continue
        if table_name not in meta_pg.tables:
            print(f"Skipping {table_name}: not found in Postgres.")
            continue

        print(f"Migrating table: {table_name}")
        sqlite_table = meta_sqlite.tables[table_name]
        pg_table = meta_pg.tables[table_name]

        # Fetch all records
        records = sqlite_conn.execute(select(sqlite_table)).fetchall()
        print(f"Found {len(records)} records in {table_name}.")

        if not records:
            continue

        # Convert records to dicts
        data_to_insert = []
        for r in records:
            data_to_insert.append(dict(r._mapping))

        # Clear existing data in Postgres table
        try:
            from sqlalchemy import text
            pg_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
            pg_conn.commit()
            print(f"Cleared existing data in {table_name}.")
        except Exception as e:
            pg_conn.rollback()
            err_str = str(e).encode('ascii', 'replace').decode('ascii')
            print(f"Warning: Could not truncate {table_name}: {err_str}")

        # Insert into Postgres
        # We might need to handle duplicates or clear the table first
        # For a clean migration, we assume the pg table is empty or we only insert missing
        try:
            pg_conn.execute(pg_table.insert(), data_to_insert)
            pg_conn.commit()
            print(f"Successfully migrated {len(records)} records into {table_name}.")
        except Exception as e:
            pg_conn.rollback()
            err_str = str(e).encode('ascii', 'replace').decode('ascii')
            print(f"Error migrating {table_name}: {err_str}")
            
    sqlite_conn.close()
    pg_conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    main()
