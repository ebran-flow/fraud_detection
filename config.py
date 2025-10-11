"""
Configuration file for Airtel Fraud Detection System
Centralizes all path configurations for easy management
"""
import os

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Data directories
UPLOADED_PDF_PATH = os.path.join(PROJECT_ROOT, "uploaded_pdfs")
RESULTS_PATH = os.path.join(PROJECT_ROOT, "results")
DETAILED_SHEETS_PATH = os.path.join(PROJECT_ROOT, "detailed_sheets")
BATCH_RESULTS_PATH = os.path.join(PROJECT_ROOT, "batch_results")
STATEMENTS_PATH = os.path.join(PROJECT_ROOT, "statements")

# CSV files
MAPPER_CSV = os.path.join(PROJECT_ROOT, "mapper.csv")
BALANCE_SUMMARY_CSV = os.path.join(RESULTS_PATH, "balance_summary.csv")

# Archive directory (external data storage)
# Update this path to point to your Airtel statements archive
STATEMENTS_ARCHIVE_DIR = os.environ.get(
    "AIRTEL_ARCHIVE_DIR",
    "/home/ebran/Developer/projects/data_score_factors/DATA/archive/UATL_extracted"
)

# Google Sheets credentials
GOOGLE_CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, "google_credentials.json")

# Create directories if they don't exist
for directory in [UPLOADED_PDF_PATH, RESULTS_PATH, DETAILED_SHEETS_PATH,
                  BATCH_RESULTS_PATH, STATEMENTS_PATH]:
    os.makedirs(directory, exist_ok=True)
