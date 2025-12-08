# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Sign and update TUF metadata for uploaded integration wheels.

This command generates and signs TUF (The Update Framework) metadata for
pointer files uploaded to S3, enabling secure distribution with cryptographic
verification.
"""
from pathlib import Path

import click

from datadog_checks.dev.tooling.commands.console import (
    CONTEXT_SETTINGS,
    abort,
    echo_info,
    echo_success,
    echo_waiting,
)


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Sign and update TUF metadata for uploaded integrations',
)
@click.option(
    '--keys-dir',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    help='Directory containing TUF signing keys (default: ~/.ddev/tuf_keys)',
)
@click.option(
    '--generate-keys',
    is_flag=True,
    help='Generate new dummy Ed25519 keys for POC (WARNING: for testing only)',
)
@click.option(
    '--output-dir',
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True),
    help='Local directory to save metadata files (default: /tmp/tuf_metadata)',
)
@click.option(
    '--aws-vault-profile',
    default=None,
    help='AWS Vault profile to use for S3 authentication (default: sso-agent-integrations-dev-account-admin)',
)
@click.option('--local', is_flag=True, help='Use local MinIO instead of AWS S3 (for development/testing)')
def sign(
    keys_dir: str | None,
    generate_keys: bool,
    output_dir: str | None,
    aws_vault_profile: str | None,
    local: bool,
) -> None:
    """
    Sign and update TUF metadata for uploaded integration pointer files.

    This command performs the following steps:

    \b
    1. Lists all pointer files in the S3 bucket
    2. Generates TUF metadata (root, targets, snapshot, timestamp)
    3. Signs metadata with Ed25519 keys from --keys-dir
    4. Uploads signed metadata to S3 metadata/ prefix

    For POC testing, use --generate-keys to create dummy Ed25519 keys.
    WARNING: These keys are NOT suitable for production use.

    AWS credentials are required for S3 access. If not available, the command
    will automatically use aws-vault with the specified profile (or the default).

    \b
    Examples:
        # Generate dummy keys and sign metadata (auto aws-vault)
        ddev release sign --generate-keys

        # Use specific aws-vault profile
        ddev release sign --generate-keys --aws-vault-profile my-profile

        # Use existing keys from custom directory
        ddev release sign --keys-dir ~/.ddev/tuf_keys

        # Sign and save to custom output directory
        ddev release sign --output-dir ./metadata_output

    \b
    Requirements:
        - Pointer files already uploaded to S3 via 'ddev release upload'

    \b
    Note: This is a POC implementation using dummy keys. Production use
    requires proper key management (HSM, KMS) and key ceremony procedures.
    """
    from datadog_checks.dev.tooling.aws_helpers import ensure_aws_credentials, get_s3_client
    from datadog_checks.dev.tooling.tuf_signing import generate_dummy_keys, generate_tuf_metadata, load_keys

    # Ensure MinIO is running for local mode, or AWS credentials for remote
    if local:
        from datadog_checks.dev.tooling.minio_manager import ensure_minio_running

        ensure_minio_running()
    else:
        ensure_aws_credentials(profile=aws_vault_profile)

    S3_BUCKET = "test-public-integration-wheels"
    S3_REGION = "eu-north-1"

    # Setup keys directory
    if keys_dir:
        keys_path = Path(keys_dir)
    else:
        keys_path = Path.home() / '.ddev' / 'tuf_keys'

    # Setup output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Path('/tmp/tuf_metadata')

    # Generate or load keys
    if generate_keys:
        echo_waiting('Generating dummy TUF keys for POC...')
        echo_info('WARNING: These are DUMMY keys for testing only!')
        keys_path.mkdir(parents=True, exist_ok=True)
        try:
            keys = generate_dummy_keys(keys_path)
            echo_success(f'Keys generated at: {keys_path}')
        except Exception as e:
            abort(f'Failed to generate keys: {e}')
    else:
        # Check if keys exist
        if not (keys_path / 'root_key').exists():
            echo_info(f'No keys found at {keys_path}')
            echo_info('Run with --generate-keys to create dummy keys for POC')
            abort('Keys not found')

        echo_info(f'Loading existing keys from: {keys_path}')
        try:
            keys = load_keys(keys_path)
            echo_success('Keys loaded successfully')
        except Exception as e:
            abort(f'Failed to load keys: {e}')

    # Initialize S3 client (local MinIO or AWS S3)
    target = "local MinIO" if local else "S3"
    echo_waiting(f'Connecting to {target}...')
    try:
        s3 = get_s3_client(local=local, region=S3_REGION)
        # Test connection by checking bucket exists
        s3.head_bucket(Bucket=S3_BUCKET)
        echo_success(f'Connected to {target} bucket: {S3_BUCKET}')
    except Exception as e:
        abort(f'Failed to connect to {target}: {e}\n\nMake sure {"MinIO container is running (check: docker ps | grep ddev-minio-local)" if local else "you have AWS credentials configured"}.')

    # Generate TUF metadata
    echo_waiting('Generating TUF metadata from S3 pointer files...')
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        generate_tuf_metadata(s3, S3_BUCKET, keys, output_path)
        echo_success('TUF metadata signed and uploaded successfully!')
        echo_info(f'\nMetadata files saved locally to: {output_path}')
        echo_info(f'Metadata uploaded to: s3://{S3_BUCKET}/metadata/')
        echo_info('\nYou can now download wheels securely using the TUF-enabled downloader.')
    except Exception as e:
        abort(f'Failed to generate TUF metadata: {e}')
