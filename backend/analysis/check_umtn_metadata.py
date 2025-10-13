#!/usr/bin/env python3
"""
Check UMTN Metadata
"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from app.services.db import SessionLocal


def main():
    """Check metadata"""
    run_id = "66ec2b21c7585"

    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT acc_prvdr_code, format, mime
            FROM metadata
            WHERE run_id = :run_id
        """), {"run_id": run_id})

        row = result.fetchone()
        if row:
            print(f"\nMetadata for {run_id}:")
            print(f"  Provider: {row[0]}")
            print(f"  Format: {row[1]}")
            print(f"  MIME: {row[2]}")

            # Simulate pdf_format property
            format_val = row[1]
            if format_val == 'format_1':
                pdf_format = 1
            elif format_val == 'format_2':
                pdf_format = 2
            elif format_val == 'excel':
                pdf_format = None
            else:
                pdf_format = None
            print(f"  PDF Format (derived): {pdf_format}")
        else:
            print(f"No metadata found for {run_id}")

    finally:
        db.close()


if __name__ == '__main__':
    main()
