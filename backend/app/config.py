"""
Configuration for Fraud Detection Backend
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
UPLOADED_PDF_PATH = PROJECT_ROOT / "uploaded_pdfs"
MAPPER_CSV = PROJECT_ROOT / "mapper.csv"

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3307"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "fraud_detection")

# SQLAlchemy database URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Application settings
APP_TITLE = "Airtel Fraud Detection System"
APP_VERSION = "2.0.0"
API_PREFIX = "/api/v1"

# File upload settings
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf"}

# Pagination
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500

# Create directories
UPLOADED_PDF_PATH.mkdir(parents=True, exist_ok=True)
