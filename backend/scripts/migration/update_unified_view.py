#!/usr/bin/env python3
"""Update unified_statements view with customer details"""
import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).parent.parent.parent / '.env')

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

engine = create_engine(
    f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
)

# Read SQL file
sql_file = Path(__file__).parent.parent.parent / 'migrations' / 'update_unified_view_with_customer_details.sql'

with open(sql_file, 'r') as f:
    sql_content = f.read()

# Split by statements and execute
with engine.connect() as conn:
    # Split by semicolon but keep multi-line statements together
    statements = []
    current_stmt = []

    for line in sql_content.split('\n'):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('--'):
            continue

        current_stmt.append(line)

        # If line ends with semicolon, we have a complete statement
        if line.endswith(';'):
            stmt = ' '.join(current_stmt)
            statements.append(stmt)
            current_stmt = []

    # Execute each statement
    for stmt in statements:
        if stmt.strip():
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception as e:
                print(f"Error executing statement: {e}")
                print(f"Statement: {stmt[:200]}...")
                raise

print("✓ unified_statements view updated successfully")
