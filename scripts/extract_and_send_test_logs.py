#!/usr/bin/env python3
"""
This script extracts sample logs from integration test YAML files and sends them to Datadog staging.

How it works:
1. Scans specified folders for *test.yaml files or processes specific files
2. Extracts sample logs from the YAML test files using configurable patterns
3. Formats logs according to Datadog's v2 logs intake API format
4. Sends extracted logs to Datadog staging environment via HTTP API
5. Supports both all-files mode and specific-files mode for flexibility

Usage:
1. Ensure you have the required environment variables set:
   - DD_API_KEY: Your Datadog API key for staging

2. Run the script:
   ```
   # Send all test files from a folder
   dd-auth --domain dd.datad0g.com python scripts/extract_and_send_test_logs.py

   # Send specific test files
   dd-auth --domain dd.datad0g.com python scripts/extract_and_send_test_logs.py --files file1.yaml file2.yaml

   # CI/CD mode (process only changed files)  
   dd-auth --domain dd.datad0g.com python scripts/extract_and_send_test_logs.py --ci-mode

   # Dry run (extract but don't send)
   python scripts/extract_and_send_test_logs.py --dry-run
   ```

   If no folder path is provided, it defaults to the current directory.
"""

import logging
import os
import sys
import json
import requests
import yaml
from envparse import Env
import argparse
from pathlib import Path
import time
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DD_API_KEY = None
DD_APP_KEY = None
STAGING_LOGS_URL = "https://http-intake.logs.datad0g.com/api/v2/logs"


def load_yaml_file(file_path: str) -> dict:
    """Load and parse a YAML file safely."""
    try:
        with open(file_path, "r", encoding='utf-8') as file:
            return yaml.safe_load(file) or {}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {file_path}: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return {}


def extract_service_name(file_path: str) -> str:
    """Extract a service name from the filename."""
    return Path(file_path).stem.replace('_tests', '').replace('_test', '').replace('-tests', '').replace('-test', '').lower()


def replace_timestamp_in_data(data: dict, timestamp_field: str, timestamp_format: Optional[str] = None) -> dict:
    """
    Recursively replace timestamp fields in nested data structures.
    
    Args:
        data: Dictionary to search for timestamp fields
        timestamp_field: Field name(s) to replace (supports dot notation like 'properties.time' or comma-separated 'field1,field2')
        timestamp_format: Format for new timestamp (ISO, epoch, etc.)
    """
    current_time = datetime.now(timezone.utc)
    
    # Determine timestamp format
    if timestamp_format == "epoch":
        new_timestamp = int(current_time.timestamp())
    elif timestamp_format == "epoch_ms":
        new_timestamp = int(current_time.timestamp() * 1000)
    else:
        # Default to ISO format
        new_timestamp = current_time.isoformat().replace('+00:00', 'Z')
    
    # Split comma-separated field paths
    field_paths = [path.strip() for path in timestamp_field.split(',')]
    
    def replace_in_dict(obj: dict, field_path: str) -> dict:
        """Replace timestamp field using dot notation with array support."""
        if '.' in field_path:
            # Handle nested fields like 'properties.time' and 'properties.authenticationDetails.0.field'
            parts = field_path.split('.')
            current = obj
            
            # Navigate to parent of target field
            for i, part in enumerate(parts[:-1]):
                if part.isdigit() and isinstance(current, list):
                    # Handle array index
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                        logging.debug(f"Navigated to array index [{part}]")
                    else:
                        logging.debug(f"Array index {part} out of bounds (array length: {len(current)})")
                        return obj
                elif part in current and isinstance(current[part], (dict, list)):
                    current = current[part]
                    logging.debug(f"Navigated to {'.'.join(parts[:i+2])}")
                else:
                    logging.debug(f"Path {field_path} not found - stopped at {part}")
                    return obj  # Path doesn't exist
            
            # Replace the target field
            target_field = parts[-1]
            if target_field.isdigit() and isinstance(current, list):
                # Handle array index replacement
                index = int(target_field)
                if 0 <= index < len(current):
                    current[index] = new_timestamp
                    logging.debug(f"Replaced array index [{target_field}] with {new_timestamp}")
                else:
                    logging.debug(f"Array index {target_field} out of bounds")
            elif isinstance(current, dict) and target_field in current:
                current[target_field] = new_timestamp
                logging.debug(f"Replaced {field_path} with {new_timestamp}")
            else:
                if isinstance(current, dict):
                    logging.debug(f"Target field {target_field} not found in {list(current.keys())}")
                else:
                    logging.debug(f"Cannot access field {target_field} on non-dict object: {type(current)}")
        else:
            # Simple field replacement - ONLY replace exact matches at current level
            if field_path in obj:
                obj[field_path] = new_timestamp
                logging.debug(f"Replaced {field_path} with {new_timestamp}")
            
            # For simple fields, also search recursively for same field name
            # (but don't recursively apply dot notation paths)
            for key, value in obj.items():
                if isinstance(value, dict):
                    replace_in_dict(value, field_path)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            replace_in_dict(item, field_path)
        
        return obj
    
    # Apply timestamp replacement for each field path
    for field_path in field_paths:
        data = replace_in_dict(data, field_path)
    
    return data


def extract_sample_logs(yaml_data: dict, file_path: str, timestamp_field: Optional[str] = None, timestamp_format: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract sample log entries from YAML test data.
    
    This function specifically handles the integration test file format:
    - Looks for 'tests' array containing test cases
    - Each test case has a 'sample' field with raw log JSON
    - Also searches for other common log patterns as fallback
    """
    logs = []
    
    # Primary: Handle integrations test format
    if 'tests' in yaml_data and isinstance(yaml_data['tests'], list):
        for i, test_case in enumerate(yaml_data['tests']):
            if isinstance(test_case, dict) and 'sample' in test_case:
                sample_data = test_case['sample']
                if isinstance(sample_data, str):
                    # Parse the YAML string block as JSON
                    try:
                        sample_json = json.loads(sample_data)
                        log_entry = create_log_entry(sample_json, file_path, f"tests[{i}].sample", timestamp_field, timestamp_format)
                        if log_entry:
                            logs.append(log_entry)
                    except json.JSONDecodeError as e:
                        logging.warning(f"Failed to parse JSON sample in {file_path}, test {i}: {e}")
                elif isinstance(sample_data, dict):
                    log_entry = create_log_entry(sample_data, file_path, f"tests[{i}].sample", timestamp_field, timestamp_format)
                    if log_entry:
                        logs.append(log_entry)
    
    # Fallback: Search for other common patterns if no tests found
    if not logs:
        log_keys = ['logs', 'sample_logs', 'test_logs', 'events', 'records', 'messages', 
                   'data', 'samples', 'examples', 'test_data', 'log_entries', 'payloads']
        
        def search_for_logs(data: Any, path: str = "") -> None:
            """Recursively search for log-like data in the YAML structure."""
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if key.lower() in [k.lower() for k in log_keys] and isinstance(value, (list, dict)):
                        if isinstance(value, list):
                            for i, item in enumerate(value):
                                if isinstance(item, (dict, str)) and item:
                                    log_entry = create_log_entry(item, file_path, f"{current_path}[{i}]", timestamp_field, timestamp_format)
                                    if log_entry:
                                        logs.append(log_entry)
                        elif isinstance(value, dict):
                            log_entry = create_log_entry(value, file_path, current_path, timestamp_field, timestamp_format)
                            if log_entry:
                                logs.append(log_entry)
                    else:
                        search_for_logs(value, current_path)
                        
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    search_for_logs(item, f"{path}[{i}]" if path else f"[{i}]")
        
        search_for_logs(yaml_data)
    
    return logs


def create_log_entry(data: Any, file_path: str, extraction_path: str, timestamp_field: Optional[str] = None, timestamp_format: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Create a properly formatted Datadog log entry."""
    if not data:
        return None
    
    # Replace timestamps if requested
    if timestamp_field and isinstance(data, dict):
        data = replace_timestamp_in_data(data.copy(), timestamp_field, timestamp_format)
    
    # Skip empty or minimal data
    if not data or (isinstance(data, str) and len(data.strip()) < 3):
        return None
    
    service_name = extract_service_name(file_path)
    file_name = Path(file_path).name
    
    # Determine which repo we're in  
    repo_name = "integrations-core"
    if "integrations-internal-core" in file_path:
        repo_name = "integrations-internal-core"
    
    # K9 approach: Use original JSON as base structure
    if isinstance(data, dict):
        log_entry = data.copy()  # Start with original JSON
    elif isinstance(data, str):
        try:
            log_entry = json.loads(data.strip())
        except json.JSONDecodeError:
            # Fallback for non-JSON strings
            log_entry = {"message": data.strip()}
    else:
        log_entry = {"message": str(data)}
    
    # Override fields to prevent conflicts (like k9 does)
    shared_fields = {
        "ddsource": repo_name,
        "service": "integration-test-extractor", 
        "host": "local-test",
        "logger.name": "integration-test-extractor",
        "integration_name": service_name,
        "test_file": file_name,
        "extracted_from": extraction_path,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Override any conflicting fields (like k9's log.update(shared_fields))
    log_entry.update(shared_fields)
    
    # Ensure we have a message field
    log_entry.setdefault("message", "Integration test log sample")
    
    return log_entry


def get_headers() -> dict:
    """Get headers for Datadog API requests."""
    return {
        "Content-Type": "application/json",
        "DD-API-KEY": DD_API_KEY
    }


def send_logs_to_staging(logs: List[Dict[str, Any]], batch_size: int = 100) -> bool:
    """Send logs to Datadog staging in batches."""
    if not logs:
        logging.info("No logs to send")
        return True
    
    headers = get_headers()
    total_batches = (len(logs) + batch_size - 1) // batch_size
    success_count = 0
    
    for i in range(0, len(logs), batch_size):
        batch = logs[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        logging.info(f"Sending batch {batch_num}/{total_batches} ({len(batch)} logs)")
        
        try:
            response = requests.post(
                STAGING_LOGS_URL,
                headers=headers,
                data=json.dumps(batch),
                timeout=30
            )
            
            if response.status_code in [200, 202]:
                logging.debug(f"Successfully sent batch {batch_num}")
                success_count += len(batch)
            else:
                logging.error(f"Failed to send batch {batch_num}: {response.status_code} {response.text}")
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for batch {batch_num}: {e}")
        
        # Small delay between batches to be respectful to the API
        if batch_num < total_batches:
            time.sleep(0.5)
    
    logging.info(f"Successfully sent {success_count}/{len(logs)} logs to staging")
    return success_count == len(logs)


def find_all_test_files(folder_path: str) -> List[str]:
    """Find all *_tests.yaml files in the specified folder recursively."""
    folder = Path(folder_path).resolve()
    logging.info(f"Scanning folder: {folder}")
    
    if not folder.exists():
        logging.error(f"Folder does not exist: {folder}")
        return []
    
    # Find all test YAML files recursively - try multiple patterns
    patterns = ["**/*_tests.yaml", "**/*test.yaml", "**/*tests.yaml"]
    test_files = []
    
    for pattern in patterns:
        found_files = list(folder.glob(pattern))
        test_files.extend(found_files)
        logging.debug(f"Pattern '{pattern}' found {len(found_files)} files")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for f in test_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)
    
    logging.info(f"Found {len(unique_files)} unique test YAML files")
    return [str(f) for f in unique_files]


def get_changed_test_files(base_branch: str = "main") -> List[str]:
    """Get test.yaml files that changed in current branch/commit for CI/CD mode."""
    try:
        # Try CI-specific methods first
        if os.environ.get('CI_MERGE_REQUEST_TARGET_BRANCH_NAME'):
            base = os.environ['CI_MERGE_REQUEST_TARGET_BRANCH_NAME']
            cmd = f"git diff --name-only origin/{base}..HEAD"
        else:
            cmd = f"git diff --name-only HEAD~1..HEAD"
        
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            check=True
        )
        
        # Filter for test YAML files
        changed_files = [
            f for f in result.stdout.strip().split('\n') 
            if f and (f.endswith('_tests.yaml') or f.endswith('test.yaml') or f.endswith('tests.yaml'))
        ]
        
        logging.info(f"Found {len(changed_files)} changed test files")
        return changed_files
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed: {e}")
        return []


def process_test_files(files_to_process: List[str], dry_run: bool = False, limit: Optional[int] = None, 
                      timestamp_field: Optional[str] = None, timestamp_format: Optional[str] = None) -> None:
    """Process the specified test YAML files and send extracted logs to staging."""
    if not files_to_process:
        logging.warning("No test YAML files found to process")
        return
    
    if timestamp_field:
        logging.info(f"Replacing timestamp field '{timestamp_field}' with current time (format: {timestamp_format or 'ISO'})")
    
    all_logs = []
    processed_files = 0
    
    for test_file in files_to_process:
        if not Path(test_file).exists():
            logging.warning(f"File not found: {test_file}")
            continue
            
        try:
            logging.debug(f"Processing: {test_file}")
            yaml_data = load_yaml_file(test_file)
            
            if yaml_data:
                logs = extract_sample_logs(yaml_data, test_file, timestamp_field, timestamp_format)
                if logs:
                    logging.info(f"Extracted {len(logs)} logs from {test_file}")
                    all_logs.extend(logs)
                    processed_files += 1
                else:
                    logging.debug(f"No logs found in {test_file}")
            else:
                logging.warning(f"Could not load YAML data from {test_file}")
                
        except Exception as e:
            logging.error(f"Error processing {test_file}: {e}")
            continue
    
    logging.info(f"Processed {processed_files} files, extracted {len(all_logs)} total logs")
    
    if limit:
        all_logs = all_logs[:limit]
        logging.info(f"Limited to {len(all_logs)} logs due to --limit flag")
    
    if not all_logs:
        logging.warning("No logs were extracted from any test files")
        return
    
    if dry_run:
        logging.info("DRY RUN MODE - logs extracted but not sent to staging")
        logging.info(f"Would send {len(all_logs)} logs to staging")
        if all_logs:
            logging.info("Sample log entry:")
            print(json.dumps(all_logs[0], indent=2))
    else:
        success = send_logs_to_staging(all_logs)
        if not success:
            logging.error("Some logs failed to send")
        else:
            logging.info("All logs sent successfully")


def validate_environment() -> bool:
    """Validate that required environment variables are set."""
    if not DD_API_KEY:
        logging.error("DD_API_KEY is required but not set")
        return False
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract sample logs from integration test YAML files and send to Datadog staging.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send all test files from folder
  python scripts/ocsf/extract_and_send_test_logs.py /path/to/folder
  
  # Send specific files
  python scripts/ocsf/extract_and_send_test_logs.py --files file1.yaml file2.yaml
  
  # CI/CD mode (only changed files)
  python scripts/ocsf/extract_and_send_test_logs.py --ci-mode
  
  # Dry run
  python scripts/ocsf/extract_and_send_test_logs.py /path/to/folder --dry-run
        """
    )
    
    # Input selection (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        "folder_path",
        type=str,
        nargs="?",
        default=None,
        help="Path to folder containing test YAML files (default: current directory)"
    )
    input_group.add_argument(
        "--files",
        nargs="+",
        help="Specific test YAML files to process"
    )
    input_group.add_argument(
        "--ci-mode",
        action="store_true",
        help="CI/CD mode: process only files changed in current commit/branch"
    )
    
    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract logs but don't send them to staging (for testing)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of log entries to process (for testing)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Timestamp replacement options
    parser.add_argument(
        "--replace-timestamp",
        type=str,
        dest="timestamp_field",
        help="Replace timestamp field(s) with current time (supports dot notation like 'properties.time' or comma-separated 'field1,field2')"
    )
    parser.add_argument(
        "--timestamp-format",
        type=str,
        choices=["iso", "epoch", "epoch_ms"],
        default="iso",
        help="Format for replacement timestamps: iso (default), epoch (seconds), epoch_ms (milliseconds)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load environment variables
    env = Env()
    DD_API_KEY = env.str("DD_API_KEY", default=None)
    DD_APP_KEY = env.str("DD_APP_KEY", default=None)
    
    if not args.dry_run and not validate_environment():
        sys.exit(1)
    
    # Determine which files to process
    files_to_process = []
    
    if args.ci_mode:
        logging.info("Running in CI/CD mode - processing only changed files")
        files_to_process = get_changed_test_files()
    elif args.files:
        logging.info(f"Processing specific files: {args.files}")
        files_to_process = args.files
    else:
        folder_path = args.folder_path or "."
        logging.info(f"Processing all test files in: {folder_path}")
        files_to_process = find_all_test_files(folder_path)
    
    try:
        process_test_files(files_to_process, dry_run=args.dry_run, limit=args.limit,
                          timestamp_field=args.timestamp_field, timestamp_format=args.timestamp_format)
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)