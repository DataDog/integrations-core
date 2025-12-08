# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
AWS authentication helpers for ddev commands.

This module provides utilities to automatically handle AWS authentication
using aws-vault when credentials are not available.
"""
import os
import subprocess
import sys


def check_aws_credentials() -> bool:
    """Check if AWS credentials are available.

    Returns:
        True if credentials are available, False otherwise
    """
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError

        sts = boto3.client('sts')
        sts.get_caller_identity()
        return True
    except (NoCredentialsError, Exception):
        return False


def exec_with_aws_vault(profile: str, command_args: list[str]) -> None:
    """Execute command with aws-vault profile.

    This function re-executes the current command with aws-vault,
    injecting AWS credentials from the specified profile.

    Args:
        profile: AWS vault profile name
        command_args: Original command arguments (sys.argv)

    Raises:
        SystemExit: Always exits after re-executing with aws-vault
    """
    # Build aws-vault command
    aws_vault_cmd = ['aws-vault', 'exec', profile, '--']
    aws_vault_cmd.extend(command_args)

    print(f"No AWS credentials found. Using aws-vault profile: {profile}")
    print(f"Executing: {' '.join(aws_vault_cmd)}")
    print()

    # Execute with aws-vault
    try:
        subprocess.run(aws_vault_cmd, check=True)
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("Error: aws-vault not found. Please install it:")
        print("  macOS: brew install aws-vault")
        print("  Linux: See https://github.com/99designs/aws-vault#installing")
        sys.exit(1)


def ensure_aws_credentials(profile: str | None = None, skip_if_set: bool = False) -> None:
    """Ensure AWS credentials are available, using aws-vault if needed.

    This function checks if AWS credentials are available. If not, it
    re-executes the current command with aws-vault.

    Args:
        profile: AWS vault profile to use (if None, uses default)
        skip_if_set: If True, skip aws-vault if any credentials exist
                     (even if they're expired or invalid)

    Note:
        This function may not return if it needs to re-exec with aws-vault
    """
    # If profile is explicitly set, always use aws-vault
    if profile:
        # Check if we're already running under aws-vault
        if os.environ.get('AWS_VAULT'):
            # Already in aws-vault, continue
            return

        # Re-exec with aws-vault
        exec_with_aws_vault(profile, sys.argv)

    # No explicit profile - check if credentials are available
    if check_aws_credentials():
        return

    # No credentials available - try default profile
    default_profile = os.environ.get('AWS_VAULT_DEFAULT_PROFILE', 'sso-agent-integrations-dev-account-admin')

    # Check if we're already running under aws-vault
    if os.environ.get('AWS_VAULT'):
        # We're in aws-vault but credentials check failed
        # This means the session might be expired
        print("Warning: Running under aws-vault but credentials check failed.")
        print("Your session may have expired. Try running the command again.")
        return

    # Re-exec with default profile
    exec_with_aws_vault(default_profile, sys.argv)


def get_default_aws_vault_profile() -> str:
    """Get the default AWS vault profile.

    Returns:
        Default profile name from environment or hardcoded default
    """
    return os.environ.get('AWS_VAULT_DEFAULT_PROFILE', 'sso-agent-integrations-dev-account-admin')


def get_s3_client(local: bool = False, region: str = 'eu-north-1'):
    """Get boto3 S3 client configured for local or remote S3.

    Args:
        local: If True, use local MinIO endpoint
        region: AWS region (ignored for local mode)

    Returns:
        Configured boto3 S3 client
    """
    import boto3

    if local:
        # Local MinIO configuration
        return boto3.client(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin',
            region_name=region,
        )
    else:
        # Standard AWS S3
        return boto3.client('s3', region_name=region)
