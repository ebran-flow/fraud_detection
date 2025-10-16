#!/usr/bin/env python3
"""
Test the simplified detection logic on a sample and compare with original results.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.processor import process_statement

# Get from environment
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')

# Create engine
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4')
Session = sessionmaker(bind=engine)

print("=" * 80)
print("TESTING SIMPLIFIED DETECTION LOGIC")
print("=" * 80)
print()
print("New Logic:")
print("- Simple majority voting")
print("- No thresholds, no minimum transaction counts")
print("- Enable if votes_for > votes_against")
print("- Default to disabled")
print()

# Test on the original problem statement first
test_run_id = '687a321075c82'

print(f"Testing on original problem statement: {test_run_id}")
print("-" * 80)

# Get original state (from Round 3)
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT balance_match, balance_diff_changes,
               uses_implicit_cashback, uses_implicit_ind02_commission
        FROM summary
        WHERE run_id = :run_id
    """), {'run_id': test_run_id})

    original = result.fetchone()
    if original:
        print(f"\nOriginal (Round 3) Results:")
        print(f"  Balance Match: {original[0]}")
        print(f"  Balance Diff Changes: {original[1]}")
        print(f"  Uses Implicit Cashback: {original[2]}")
        print(f"  Uses Implicit IND02: {original[3]}")

# Delete and reprocess with simplified logic
print(f"\n\nReprocessing with simplified detection...")
with engine.connect() as conn:
    conn.execute(text("DELETE FROM uatl_processed_statements WHERE run_id = :run_id"), {'run_id': test_run_id})
    conn.execute(text("DELETE FROM summary WHERE run_id = :run_id"), {'run_id': test_run_id})
    conn.commit()

db = Session()
result = process_statement(db, test_run_id)
db.close()

# Get new results
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT balance_match, balance_diff_changes,
               uses_implicit_cashback, uses_implicit_ind02_commission
        FROM summary
        WHERE run_id = :run_id
    """), {'run_id': test_run_id})

    new = result.fetchone()
    if new:
        print(f"\nNew (Simplified) Results:")
        print(f"  Balance Match: {new[0]}")
        print(f"  Balance Diff Changes: {new[1]}")
        print(f"  Uses Implicit Cashback: {new[2]}")
        print(f"  Uses Implicit IND02: {new[3]}")

        if original:
            print(f"\n\nComparison:")
            print(f"  Balance Match: {original[0]} → {new[0]}")
            print(f"  Balance Diff Changes: {original[1]} → {new[1]} ({'+' if new[1] > original[1] else ''}{new[1] - original[1]})")
            print(f"  Cashback: {original[2]} → {new[2]}")
            print(f"  IND02: {original[3]} → {new[3]}")

            if new[1] < original[1]:
                print(f"\n✓ IMPROVEMENT: {original[1] - new[1]} fewer balance diff changes")
            elif new[1] > original[1]:
                print(f"\n✗ DEGRADATION: {new[1] - original[1]} more balance diff changes")
            else:
                print(f"\n= NO CHANGE")

print("\n\n" + "=" * 80)
print("Now testing on a larger sample...")
print("=" * 80)

# Select sample statements
with engine.connect() as conn:
    # Get 10 statements that currently have cashback enabled
    result = conn.execute(text("""
        SELECT s.run_id, s.balance_match, s.balance_diff_changes,
               s.uses_implicit_cashback, s.uses_implicit_ind02_commission
        FROM summary s
        JOIN metadata m ON s.run_id = m.run_id
        WHERE m.acc_prvdr_code = 'UATL'
        AND s.uses_implicit_cashback = 1
        AND s.balance_match = 'Failed'
        ORDER BY RAND()
        LIMIT 10
    """))

    sample_statements = []
    for row in result:
        sample_statements.append({
            'run_id': row[0],
            'old_balance_match': row[1],
            'old_diff_changes': row[2],
            'old_cashback': bool(row[3]),
            'old_ind02': bool(row[4])
        })

print(f"\nSelected {len(sample_statements)} Failed statements with cashback enabled")
print()

improvements = 0
degradations = 0
unchanged = 0

for i, stmt in enumerate(sample_statements):
    print(f"\n{i+1}. Testing {stmt['run_id']}...")

    # Delete and reprocess
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM uatl_processed_statements WHERE run_id = :run_id"), {'run_id': stmt['run_id']})
        conn.execute(text("DELETE FROM summary WHERE run_id = :run_id"), {'run_id': stmt['run_id']})
        conn.commit()

    db = Session()
    process_statement(db, stmt['run_id'])
    db.close()

    # Get new results
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT balance_match, balance_diff_changes,
                   uses_implicit_cashback, uses_implicit_ind02_commission
            FROM summary
            WHERE run_id = :run_id
        """), {'run_id': stmt['run_id']})

        row = result.fetchone()
        if row:
            new_match = row[0]
            new_diff = row[1]
            new_cashback = bool(row[2])
            new_ind02 = bool(row[3])

            print(f"   Old: {stmt['old_balance_match']}, diff={stmt['old_diff_changes']}, cashback={stmt['old_cashback']}")
            print(f"   New: {new_match}, diff={new_diff}, cashback={new_cashback}")

            diff_change = new_diff - stmt['old_diff_changes']
            if diff_change < 0:
                print(f"   ✓ IMPROVED by {-diff_change}")
                improvements += 1
            elif diff_change > 0:
                print(f"   ✗ DEGRADED by {diff_change}")
                degradations += 1
            else:
                print(f"   = UNCHANGED")
                unchanged += 1

print("\n\n" + "=" * 80)
print("SAMPLE RESULTS SUMMARY")
print("=" * 80)
print(f"\nImprovements: {improvements}")
print(f"Degradations: {degradations}")
print(f"Unchanged: {unchanged}")

if improvements > degradations:
    print(f"\n✓ NET IMPROVEMENT: {improvements - degradations} more statements improved")
elif degradations > improvements:
    print(f"\n✗ NET DEGRADATION: {degradations - improvements} more statements degraded")
else:
    print(f"\n= NEUTRAL: Equal improvements and degradations")

print("\n" + "=" * 80)
