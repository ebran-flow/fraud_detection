#!/usr/bin/env python3
"""
Extract Compressed Statements Script

Extracts first file from each ZIP archive, detects format, and saves with proper extension.

Usage:
    python extract_statements.py              # Extract all files
    python extract_statements.py --dry-run    # Preview without extracting
"""

import zipfile
import argparse
import logging
from pathlib import Path
import magic
import shutil
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract_statements.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
COMPRESSED_DIR = Path("/home/ebran/Developer/projects/airtel_fraud_detection/docs/data/UATL/compressed")
EXTRACTED_DIR = Path("/home/ebran/Developer/projects/airtel_fraud_detection/docs/data/UATL/extracted")


def detect_file_type(file_path: Path) -> str:
    """Detect file type. Returns: 'pdf', 'csv', or 'xlsx'"""
    mime = magic.from_file(str(file_path), mime=True)

    if mime == 'application/pdf':
        return 'pdf'
    elif mime in ['text/csv', 'text/plain']:
        return 'csv'
    elif mime in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
        return 'xlsx'

    return 'csv'  # Default to csv


def is_zip_file(file_path: Path) -> bool:
    """Check if file is ZIP by magic bytes"""
    try:
        with open(file_path, 'rb') as f:
            return f.read(2) == b'PK'
    except:
        return False


def extract_file(zip_path: Path, extracted_dir: Path, dry_run: bool = False):
    """Extract first file from ZIP and save with proper extension"""

    # Get base name (remove .zip if present)
    base_name = zip_path.stem if zip_path.suffix == '.zip' else zip_path.name

    # Check if already extracted
    if list(extracted_dir.glob(f"{base_name}.*")):
        logger.info(f"⏭️  Already extracted: {base_name}")
        return True

    # Check if it's a ZIP
    if not is_zip_file(zip_path):
        logger.warning(f"❌ Not a ZIP file: {zip_path.name}")
        return False

    try:
        # Extract first file to temp
        with zipfile.ZipFile(zip_path, 'r') as zf:
            files = [f for f in zf.namelist() if not f.endswith('/') and not f.startswith('__MACOSX')]

            if not files:
                logger.warning(f"❌ No files in ZIP: {zip_path.name}")
                return False

            temp_path = extracted_dir / f"temp_{files[0]}"

            if dry_run:
                logger.info(f"[DRY RUN] Would extract from: {zip_path.name}")
                return True

            with zf.open(files[0]) as source, open(temp_path, 'wb') as target:
                shutil.copyfileobj(source, target)

        # Detect type and rename
        file_type = detect_file_type(temp_path)
        final_path = extracted_dir / f"{base_name}.{file_type}"
        shutil.move(str(temp_path), str(final_path))

        logger.info(f"✅ Extracted: {final_path.name}")
        return True

    except Exception as e:
        logger.error(f"❌ Error extracting {zip_path.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Extract compressed statement files')
    parser.add_argument('--dry-run', action='store_true', help='Preview without extracting')
    args = parser.parse_args()

    # Validate paths
    if not COMPRESSED_DIR.exists():
        logger.error(f"❌ Directory not found: {COMPRESSED_DIR}")
        return 1

    if not args.dry_run:
        EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    # Start
    start_time = datetime.now()
    logger.info(f"\n{'='*70}")
    logger.info(f"EXTRACT STATEMENTS - {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"{'='*70}\n")

    # Process all files
    files = sorted(COMPRESSED_DIR.iterdir())
    logger.info(f"Found {len(files)} files\n")

    success = 0
    skipped = 0
    errors = 0

    for idx, file_path in enumerate(files, 1):
        if file_path.is_file():
            logger.info(f"[{idx}/{len(files)}] {file_path.name}")
            result = extract_file(file_path, EXTRACTED_DIR, args.dry_run)

            if result:
                if "Already extracted" in str(result):
                    skipped += 1
                else:
                    success += 1
            else:
                errors += 1

    # Summary
    duration = datetime.now() - start_time
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Total files:       {len(files)}")
    logger.info(f"✅ Extracted:      {success}")
    logger.info(f"⏭️  Already done:   {skipped}")
    logger.info(f"❌ Errors:         {errors}")
    logger.info(f"Duration:          {duration}")
    logger.info(f"{'='*70}\n")

    return 0


if __name__ == '__main__':
    exit(main())
