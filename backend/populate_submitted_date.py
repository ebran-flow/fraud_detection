#!/usr/bin/env python3
"""
Populate submitted_date from mapper.csv
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.services.db import engine
from app.services.mapper import load_mapper

def populate_submitted_dates():
    """Populate submitted_date from mapper.csv"""
    print("Loading mapper.csv...")
    mapper_df = load_mapper()

    if mapper_df.empty:
        print("Warning: mapper.csv is empty or not found")
        return 0

    print(f"Found {len(mapper_df)} records in mapper.csv")

    # Filter to only records with created_date
    mapper_df = mapper_df[mapper_df['created_date'].notna()]
    print(f"Records with created_date: {len(mapper_df)}")

    updated_count = 0

    with engine.connect() as conn:
        for idx, row in mapper_df.iterrows():
            run_id = row['run_id']
            created_date = row['created_date']

            try:
                # Parse the date if it's a string
                if isinstance(created_date, str):
                    created_date = datetime.strptime(created_date, '%Y-%m-%d').date()

                # Update metadata table
                result = conn.execute(
                    text("""
                        UPDATE metadata
                        SET submitted_date = :created_date
                        WHERE run_id = :run_id
                          AND submitted_date IS NULL
                    """),
                    {"run_id": run_id, "created_date": created_date}
                )

                if result.rowcount > 0:
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"  Updated {updated_count} records...")
                        conn.commit()

            except Exception as e:
                print(f"  Error updating {run_id}: {e}")

        conn.commit()

    print(f"\n✅ Updated submitted_date for {updated_count} records")
    return updated_count

if __name__ == "__main__":
    print("=" * 60)
    print("Populate submitted_date from mapper.csv")
    print("=" * 60)
    populate_submitted_dates()
