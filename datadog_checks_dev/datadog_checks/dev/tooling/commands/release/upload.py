# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from datadog_checks.dev.fs import basepath, chdir, dir_exists, resolve_path
from datadog_checks.dev.subprocess import run_command
from datadog_checks.dev.tooling.commands.console import CONTEXT_SETTINGS, abort, echo_success, echo_waiting
from datadog_checks.dev.tooling.constants import get_root
from datadog_checks.dev.tooling.release import build_package, upload_package
from datadog_checks.dev.tooling.utils import complete_valid_checks, get_valid_checks


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Build and upload a check to S3 or PyPI')
@click.argument('check', shell_complete=complete_valid_checks)
@click.option('--sdist', '-s', is_flag=True)
@click.option('--dry-run', '-n', is_flag=True)
@click.option('--pypi', is_flag=True, help='Upload to PyPI instead of S3')
@click.option('--public', is_flag=True, help='Upload both wheel and pointer files to S3 (for public packages)')
@click.option(
    '--aws-vault-profile',
    default=None,
    help='AWS Vault profile to use for S3 authentication (default: sso-agent-integrations-dev-account-admin)',
)
@click.pass_context
def upload(ctx, check, sdist, dry_run, pypi, public, aws_vault_profile):
    """Release a specific check to S3 (default) or PyPI (with --pypi flag) as it is on the repo HEAD.

    For S3 uploads, AWS credentials are required. If not available, the command will
    automatically use aws-vault with the specified profile (or the default profile).

    Examples:
        # Upload with automatic aws-vault (uses default profile)
        ddev release upload --public postgres

        # Upload with specific aws-vault profile
        ddev release upload --public postgres --aws-vault-profile my-profile

        # Upload to PyPI instead of S3
        ddev release upload --pypi postgres
    """
    if check in get_valid_checks():
        check_dir = os.path.join(get_root(), check)
    else:
        check_dir = resolve_path(check)
        if not dir_exists(check_dir):
            abort(f'`{check}` is not an Agent-based Integration or Python package')

        check = basepath(check_dir)

    if pypi:
        # Upload to PyPI
        # retrieve credentials
        pypi_config = ctx.obj.get('pypi', {})
        username = pypi_config.get('user') or os.getenv('TWINE_USERNAME')
        password = pypi_config.get('pass') or os.getenv('TWINE_PASSWORD')
        if not (username and password):
            abort('This requires pypi.user and pypi.pass configuration. Please see `ddev config -h`.')

        auth_env_vars = {'TWINE_USERNAME': username, 'TWINE_PASSWORD': password}
        echo_waiting(f'Building and publishing `{check}` to PyPI...')

        with chdir(check_dir, env_vars=auth_env_vars):
            result = build_package(check_dir, sdist)
            if result.code != 0:
                abort(result.stdout, result.code)
            echo_waiting('Uploading the package...')
            if not dry_run:
                result = run_command(f'twine upload --skip-existing dist{os.path.sep}*')
                if result.code != 0:
                    abort(code=result.code)
    else:
        # Upload to S3
        from datadog_checks.dev.tooling.aws_helpers import ensure_aws_credentials
        from datadog_checks.dev.tooling.utils import get_version_string

        # Ensure AWS credentials are available (may re-exec with aws-vault)
        ensure_aws_credentials(profile=aws_vault_profile)

        echo_waiting(f'Building and uploading `{check}` to S3...')

        result = build_package(check_dir, sdist)
        if result.code != 0:
            abort(result.stdout, result.code)

        version = get_version_string(check)
        upload_type = "wheel and pointer files" if public else "wheel file"
        echo_waiting(f'Uploading the package {upload_type} (version {version})...')

        if not dry_run:
            try:
                upload_package(check_dir, version, public=public)
            except Exception as e:
                abort(f'Failed to upload to S3: {e}')

    echo_success('Success!')
