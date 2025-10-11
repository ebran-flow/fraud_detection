import pandas as pd
import sys
import os

# Add parent directory to path to import helpers from data_score_factors
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data_score_factors'))

try:
    from helpers import connect_to_database_engine, cleanup
except ImportError:
    print("Error: helpers module not found. Please ensure data_score_factors project is accessible.")
    print("Expected path: /home/ebran/Developer/projects/data_score_factors/helpers.py")
    sys.exit(1)

# Import configuration
from config import MAPPER_CSV

MAPPER_CSV_PATH = MAPPER_CSV

def get_statement_requests(db_con):
    """
    Fetch statement request data for UATL and UMTN with RM details.
    """
    query = """
        SELECT
            s.flow_req_id AS run_id,
            s.acc_number,
            s.alt_acc_num,
            s.acc_prvdr_code,
            s.status,
            s.object_key,
            s.lambda_status,
            p.id AS rm_id,
            CONCAT_WS(' ', p.first_name, p.middle_name, p.last_name) AS rm_name,
            DATE(s.created_at) AS created_date
        FROM
            partner_acc_stmt_requests s
            LEFT JOIN app_users a on a.id = s.created_by
            LEFT JOIN persons p ON p.id = a.person_id
        WHERE
            s.acc_prvdr_code IN ('UMTN', 'UATL');
    """
    return pd.read_sql(query, db_con)

def main():
    print("🔗 Connecting to database...")
    engine = connect_to_database_engine('LIVE')

    try:
        with engine.begin() as db_con:
            print("📥 Fetching statement request data for UATL and UMTN...")
            df = get_statement_requests(db_con)
            print(f"✅ Retrieved {len(df)} records.")

            if df.empty:
                print("⚠️ No records found.")
                return

            print(f"💾 Saving results to {MAPPER_CSV_PATH}")
            df.to_csv(MAPPER_CSV_PATH, index=False)
            print("✅ CSV saved successfully.")

    except Exception as e:
        print(f"❌ Error during processing: {e}")

    finally:
        cleanup(engine)
        print("🔌 Database connection closed.")

if __name__ == "__main__":
    main()
