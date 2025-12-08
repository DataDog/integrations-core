# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
MinIO container management for local S3 development.

This module automatically manages a MinIO Docker container for local testing
of S3 upload and TUF signing workflows.
"""
import subprocess
import time


MINIO_CONTAINER_NAME = "ddev-minio-local"
MINIO_PORT = 9000
MINIO_CONSOLE_PORT = 9001
MINIO_ROOT_USER = "minioadmin"
MINIO_ROOT_PASSWORD = "minioadmin"
BUCKET_NAME = "test-public-integration-wheels"


def is_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        subprocess.run(['docker', 'info'], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def is_minio_running() -> bool:
    """Check if MinIO container is running."""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={MINIO_CONTAINER_NAME}', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return MINIO_CONTAINER_NAME in result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def container_exists() -> bool:
    """Check if MinIO container exists (running or stopped)."""
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--filter', f'name={MINIO_CONTAINER_NAME}', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return MINIO_CONTAINER_NAME in result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def start_minio() -> None:
    """Start MinIO container, creating it if necessary."""
    from datadog_checks.dev.tooling.commands.console import echo_info, echo_success, echo_waiting

    if is_minio_running():
        echo_info('MinIO is already running')
        return

    if container_exists():
        echo_waiting('Starting existing MinIO container...')
        subprocess.run(['docker', 'start', MINIO_CONTAINER_NAME], check=True, timeout=30)
    else:
        echo_waiting('Creating and starting MinIO container...')
        subprocess.run(
            [
                'docker',
                'run',
                '-d',
                '--name',
                MINIO_CONTAINER_NAME,
                '-p',
                f'{MINIO_PORT}:9000',
                '-p',
                f'{MINIO_CONSOLE_PORT}:9001',
                '-e',
                f'MINIO_ROOT_USER={MINIO_ROOT_USER}',
                '-e',
                f'MINIO_ROOT_PASSWORD={MINIO_ROOT_PASSWORD}',
                'minio/minio',
                'server',
                '/data',
                '--console-address',
                ':9001',
            ],
            check=True,
            timeout=60,
        )

    # Wait for MinIO to be ready
    echo_waiting('Waiting for MinIO to be ready...')
    for i in range(30):
        try:
            import urllib.request

            urllib.request.urlopen(f'http://localhost:{MINIO_PORT}/minio/health/live', timeout=1)
            break
        except Exception:
            if i == 29:
                raise RuntimeError('MinIO failed to start within 30 seconds')
            time.sleep(1)

    # Create bucket and set permissions
    echo_waiting(f'Creating bucket {BUCKET_NAME}...')
    setup_commands = f"""
mc alias set local http://localhost:9000 {MINIO_ROOT_USER} {MINIO_ROOT_PASSWORD}
mc mb local/{BUCKET_NAME} 2>&1 || echo 'Bucket already exists'
mc anonymous set download local/{BUCKET_NAME}
"""
    subprocess.run(['docker', 'exec', MINIO_CONTAINER_NAME, 'sh', '-c', setup_commands], check=True, timeout=30)

    echo_success('MinIO started successfully!')
    echo_info(f'Console: http://localhost:{MINIO_CONSOLE_PORT}')
    echo_info(f'API: http://localhost:{MINIO_PORT}')
    echo_info(f'Credentials: {MINIO_ROOT_USER}/{MINIO_ROOT_PASSWORD}')


def stop_minio() -> None:
    """Stop MinIO container."""
    from datadog_checks.dev.tooling.commands.console import echo_info, echo_success

    if is_minio_running():
        echo_info('Stopping MinIO container...')
        subprocess.run(['docker', 'stop', MINIO_CONTAINER_NAME], check=True, timeout=30)
        echo_success('MinIO stopped')
    else:
        echo_info('MinIO is not running')


def ensure_minio_running() -> None:
    """Ensure MinIO is running, starting it if necessary."""
    from datadog_checks.dev.tooling.commands.console import abort

    if not is_docker_available():
        abort('Docker is not available. Please install Docker and ensure it is running.')

    if not is_minio_running():
        start_minio()
