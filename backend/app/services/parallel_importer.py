"""
Parallel Import Processor
Uses multiprocessing to import multiple statements simultaneously
Optimized for multi-core systems (i5-12400: 12 threads)
"""
import os
import logging
from typing import List, Dict, Any
from multiprocessing import Pool, cpu_count
from functools import partial
import time

logger = logging.getLogger(__name__)


def import_single_file(file_info: Dict[str, Any], db_config: Dict[str, str]) -> Dict[str, Any]:
    """
    Import a single file (runs in separate process)

    Args:
        file_info: Dict with 'file_path', 'run_id', 'provider_code'
        db_config: Database connection configuration

    Returns:
        Import result dictionary
    """
    # Import here to avoid pickle issues with multiprocessing
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from ..services import crud_v2 as crud
    from ..services.parsers.uatl_parser import parse_uatl_pdf
    from ..services.parsers.uatl_csv_parser import parse_uatl_csv
    from ..services.parsers.umtn_parser import parse_umtn_excel
    from ..models.metadata import Metadata

    file_path = file_info['file_path']
    run_id = file_info['run_id']
    provider_code = file_info['provider_code']

    start_time = time.time()

    try:
        # Create database connection for this process
        db_url = f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        logger.info(f"[Worker {os.getpid()}] Importing {file_path} (run_id: {run_id}, provider: {provider_code})")

        # Determine file type and parse
        file_ext = os.path.splitext(file_path)[1].lower()

        if provider_code == 'UATL':
            if file_ext == '.pdf':
                raw_statements, metadata_dict = parse_uatl_pdf(file_path, run_id)
            elif file_ext in ['.csv', '.gz']:
                raw_statements, metadata_dict = parse_uatl_csv(file_path, run_id)
            else:
                raise ValueError(f"Unsupported file type for UATL: {file_ext}")

        elif provider_code == 'UMTN':
            if file_ext in ['.xlsx', '.xls', '.csv']:
                raw_statements, metadata_dict = parse_umtn_excel(file_path, run_id)
            else:
                raise ValueError(f"Unsupported file type for UMTN: {file_ext}")
        else:
            raise ValueError(f"Unknown provider code: {provider_code}")

        # Save to database
        # 1. Create metadata
        metadata = Metadata(**metadata_dict)
        db.add(metadata)
        db.commit()

        # 2. Bulk insert raw statements
        if raw_statements:
            crud.bulk_create_raw(db, provider_code, raw_statements)
            db.commit()

        elapsed_time = time.time() - start_time

        result = {
            'run_id': run_id,
            'provider_code': provider_code,
            'file_path': file_path,
            'status': 'success',
            'num_transactions': len(raw_statements),
            'elapsed_time': elapsed_time,
            'worker_pid': os.getpid()
        }

        logger.info(f"[Worker {os.getpid()}] Successfully imported {run_id} ({len(raw_statements)} txns) in {elapsed_time:.2f}s")

        db.close()
        return result

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[Worker {os.getpid()}] Error importing {file_path}: {e}")

        return {
            'run_id': run_id,
            'provider_code': provider_code,
            'file_path': file_path,
            'status': 'error',
            'error': str(e),
            'elapsed_time': elapsed_time,
            'worker_pid': os.getpid()
        }


def parallel_import_files(file_list: List[Dict[str, Any]], db_config: Dict[str, str],
                          num_workers: int = None) -> List[Dict[str, Any]]:
    """
    Import multiple files in parallel using multiprocessing

    Args:
        file_list: List of dicts with 'file_path', 'run_id', 'provider_code'
        db_config: Database connection config (host, port, user, password, database)
        num_workers: Number of parallel workers (default: CPU count - 1)

    Returns:
        List of import results
    """
    if num_workers is None:
        # Use environment variable or default to CPU count - 1
        num_workers = int(os.getenv('PARALLEL_IMPORT_WORKERS', cpu_count() - 1))

    # Ensure at least 1 worker
    num_workers = max(1, num_workers)

    logger.info(f"Starting parallel import with {num_workers} workers for {len(file_list)} files")
    start_time = time.time()

    # Create partial function with db_config
    import_func = partial(import_single_file, db_config=db_config)

    # Use multiprocessing Pool
    with Pool(processes=num_workers) as pool:
        results = pool.map(import_func, file_list)

    elapsed_time = time.time() - start_time

    # Calculate statistics
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'error')
    total_transactions = sum(r.get('num_transactions', 0) for r in results if r['status'] == 'success')

    logger.info(f"Parallel import completed in {elapsed_time:.2f}s")
    logger.info(f"Results: {successful} successful, {failed} failed, {total_transactions} total transactions")
    logger.info(f"Throughput: {len(file_list) / elapsed_time:.2f} files/sec, {total_transactions / elapsed_time:.2f} txns/sec")

    return results


def get_optimal_worker_count() -> int:
    """
    Determine optimal number of workers based on system resources

    For i5-12400 (6P+0E cores, 12 threads):
    - Reserve 4 threads for system/MySQL/FastAPI
    - Use 8 threads for import workers
    """
    total_cpus = cpu_count()

    # Reserve 25-30% for system
    optimal_workers = int(total_cpus * 0.7)

    # Minimum 2, maximum 16
    optimal_workers = max(2, min(optimal_workers, 16))

    return optimal_workers


# Example usage for batch import API endpoint
def batch_import_from_directory(directory: str, provider_code: str, db_config: Dict[str, str]) -> Dict[str, Any]:
    """
    Import all files from a directory in parallel

    Args:
        directory: Path to directory containing statement files
        provider_code: 'UATL' or 'UMTN'
        db_config: Database configuration

    Returns:
        Summary of import results
    """
    import uuid

    # Scan directory for files
    file_list = []

    if provider_code == 'UATL':
        extensions = ['.pdf', '.csv', '.gz']
    elif provider_code == 'UMTN':
        extensions = ['.xlsx', '.xls', '.csv']
    else:
        raise ValueError(f"Unknown provider code: {provider_code}")

    for filename in os.listdir(directory):
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in extensions:
            file_path = os.path.join(directory, filename)
            run_id = str(uuid.uuid4()).replace('-', '')[:16]

            file_list.append({
                'file_path': file_path,
                'run_id': run_id,
                'provider_code': provider_code
            })

    logger.info(f"Found {len(file_list)} files to import from {directory}")

    if not file_list:
        return {
            'status': 'no_files',
            'message': f'No files found in {directory}',
            'results': []
        }

    # Import in parallel
    results = parallel_import_files(file_list, db_config)

    return {
        'status': 'completed',
        'total_files': len(file_list),
        'successful': sum(1 for r in results if r['status'] == 'success'),
        'failed': sum(1 for r in results if r['status'] == 'error'),
        'results': results
    }
