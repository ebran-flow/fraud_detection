#!/usr/bin/env python3
"""
Create temp_fraud_detection database with same schema as fraud_detection
For testing pypdfium2 vs pdfplumber performance
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3307')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def create_temp_database():
    """Create temp_fraud_detection database"""
    # Connect to MySQL
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/mysql'
    )

    with engine.connect() as conn:
        conn.execute(text('DROP DATABASE IF EXISTS temp_fraud_detection'))
        conn.commit()
        conn.execute(text('CREATE DATABASE temp_fraud_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
        conn.commit()
        print('✅ Database temp_fraud_detection created')

def create_tables():
    """Create tables in temp_fraud_detection"""
    engine = create_engine(
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/temp_fraud_detection'
    )

    # Read schema file
    schema_file = Path(__file__).parent / 'create_all_tables.sql'
    with open(schema_file, 'r') as f:
        sql_content = f.read()

    # Extract CREATE TABLE statements
    statements = []
    current = []
    in_create = False

    for line in sql_content.split('\n'):
        if 'CREATE TABLE' in line:
            in_create = True
            current = [line]
        elif in_create:
            current.append(line)
            if line.strip().endswith(';'):
                statements.append('\n'.join(current))
                current = []
                in_create = False

    print(f'\nCreating {len(statements)} tables...')

    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
                # Extract table name
                table_name = stmt.split('`')[1]
                print(f'✅ Created table: {table_name}')
            except Exception as e:
                print(f'❌ Error: {str(e)[:100]}')

    # Verify
    with engine.connect() as conn:
        result = conn.execute(text('SHOW TABLES'))
        tables = [row[0] for row in result]
        print(f'\n✅ Total tables created: {len(tables)}')
        print(f'Tables: {", ".join(tables)}')

if __name__ == '__main__':
    print('=' * 80)
    print('CREATING TEMP_FRAUD_DETECTION DATABASE')
    print('=' * 80)

    create_temp_database()
    create_tables()

    print('\n' + '=' * 80)
    print('✅ TEMP DATABASE READY FOR TESTING')
    print('=' * 80)
