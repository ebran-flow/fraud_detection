#!/usr/bin/env python3
"""
Cross-Platform MySQL Backup Script
Works with MySQL in Docker or standalone
Compatible with MySQL 5.7, 8.0+
Platform: Windows, Linux, Mac
Reads credentials from .env file
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    print("Error: .env file not found")
    sys.exit(1)

load_dotenv(env_path)

# Configuration (read from .env with defaults)
CONFIG = {
    'docker_container': os.getenv('DOCKER_CONTAINER', 'mysql-fraud-detection'),
    'db_host': os.getenv('DB_HOST', 'localhost'),
    'db_port': os.getenv('DB_PORT', '3307'),
    'db_user': os.getenv('DB_USER', 'root'),
    'db_password': os.getenv('DB_PASSWORD', 'root'),
    'db_name': os.getenv('DB_NAME', 'fraud_detection'),
    'backup_dir': './backups',
}

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

    @staticmethod
    def disable():
        """Disable colors on Windows if not supported"""
        if os.name == 'nt':
            Colors.GREEN = ''
            Colors.YELLOW = ''
            Colors.RED = ''
            Colors.NC = ''

def print_colored(text, color=''):
    """Print colored text"""
    print(f"{color}{text}{Colors.NC}")

def check_docker():
    """Check if Docker is running"""
    try:
        subprocess.run(['docker', 'info'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_container(container_name):
    """Check if Docker container exists"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            check=True
        )
        return container_name in result.stdout.split('\n')
    except subprocess.CalledProcessError:
        return False

def get_mysqldump_args(db_name):
    """Get mysqldump arguments for cross-version compatibility"""
    return [
        '--single-transaction',           # Consistent backup without locking
        '--routines',                     # Include stored procedures
        '--triggers',                     # Include triggers
        '--events',                       # Include events
        '--default-character-set=utf8mb4',  # UTF-8 support
        '--set-charset',                  # Add SET NAMES to output
        '--no-tablespaces',              # Avoid permission issues
        '--column-statistics=0',         # MySQL 8.0+ compatibility
        '--skip-comments',               # Remove version-specific comments
        '--compact',                     # More compact output
        '--skip-lock-tables',            # Don't lock tables
        db_name
    ]

def backup_via_docker(config, backup_file):
    """Backup database via Docker exec"""
    print_colored("Using Docker exec method...", Colors.YELLOW)

    mysqldump_args = [
        '--host=localhost',
        '--port=3306',  # Internal port
        f'--user={config["db_user"]}',
        f'--password={config["db_password"]}',
    ] + get_mysqldump_args(config['db_name'])

    cmd = ['docker', 'exec', config['docker_container'], 'mysqldump'] + mysqldump_args

    with open(backup_file, 'w', encoding='utf8') as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

    return result.returncode == 0, result.stderr

def backup_direct(config, backup_file):
    """Backup database via direct connection"""
    print_colored("Using direct connection method...", Colors.YELLOW)

    mysqldump_args = [
        f'--host={config["db_host"]}',
        f'--port={config["db_port"]}',
        f'--user={config["db_user"]}',
        f'--password={config["db_password"]}',
    ] + get_mysqldump_args(config['db_name'])

    cmd = ['mysqldump'] + mysqldump_args

    with open(backup_file, 'w', encoding='utf8') as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

    return result.returncode == 0, result.stderr

def compress_backup(backup_file):
    """Compress backup file with gzip"""
    import gzip

    compressed_file = f"{backup_file}.gz"
    print_colored(f"\nCompressing to {compressed_file}...", Colors.YELLOW)

    with open(backup_file, 'rb') as f_in:
        with gzip.open(compressed_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Remove original
    os.remove(backup_file)

    return compressed_file

def format_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def list_recent_backups(backup_dir, limit=5):
    """List recent backups"""
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return []

    backups = sorted(
        backup_path.glob('*_backup_*.sql*'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:limit]

    return backups

def main():
    """Main backup function"""
    # Disable colors on Windows if needed
    if os.name == 'nt':
        Colors.disable()

    print_colored("=" * 60, Colors.GREEN)
    print_colored("MySQL Backup Script - Cross-Platform Compatible", Colors.GREEN)
    print_colored("=" * 60, Colors.GREEN)
    print()

    config = CONFIG

    # Create backup directory
    backup_dir = Path(config['backup_dir'])
    backup_dir.mkdir(exist_ok=True)

    # Create backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{config['db_name']}_backup_{timestamp}.sql"

    print_colored(f"Database: {config['db_name']}", Colors.YELLOW)
    print_colored(f"Backup File: {backup_file}", Colors.YELLOW)
    print()

    # Determine backup method
    use_docker = False
    if check_docker():
        if check_container(config['docker_container']):
            use_docker = True
            print_colored(f"✓ Docker container '{config['docker_container']}' found", Colors.GREEN)
        else:
            print_colored(f"⚠ Container '{config['docker_container']}' not found", Colors.YELLOW)
    else:
        print_colored("⚠ Docker not running or not installed", Colors.YELLOW)

    print()
    print_colored("Starting backup...", Colors.GREEN)

    # Perform backup
    try:
        if use_docker:
            success, error = backup_via_docker(config, backup_file)
        else:
            success, error = backup_direct(config, backup_file)

        if not success:
            print_colored(f"\n✗ Backup failed!", Colors.RED)
            if error:
                print_colored(f"Error: {error}", Colors.RED)
            sys.exit(1)

        # Check if backup file exists and has content
        if not backup_file.exists() or backup_file.stat().st_size == 0:
            print_colored(f"\n✗ Backup file is empty or doesn't exist!", Colors.RED)
            sys.exit(1)

        backup_size = format_size(backup_file.stat().st_size)

        print()
        print_colored("✓ Backup completed successfully!", Colors.GREEN)
        print_colored(f"  File: {backup_file}", Colors.GREEN)
        print_colored(f"  Size: {backup_size}", Colors.GREEN)

        # Ask for compression
        print()
        compress = input("Compress backup with gzip? (y/n): ").strip().lower()
        if compress == 'y':
            compressed_file = compress_backup(backup_file)
            compressed_size = format_size(Path(compressed_file).stat().st_size)
            print_colored(f"✓ Compressed: {compressed_file} ({compressed_size})", Colors.GREEN)

        # List recent backups
        print()
        print_colored("Recent backups:", Colors.GREEN)
        for backup in list_recent_backups(backup_dir):
            size = format_size(backup.stat().st_size)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"  {backup.name:50s} {size:>10s}  {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

        print()
        print_colored("=" * 60, Colors.GREEN)
        print_colored("Backup completed successfully!", Colors.GREEN)
        print_colored("=" * 60, Colors.GREEN)

    except Exception as e:
        print_colored(f"\n✗ Error: {e}", Colors.RED)
        sys.exit(1)

if __name__ == '__main__':
    main()
