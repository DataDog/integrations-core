# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from ....utils import chdir, copy_path, create_file, dir_exists, path_join, temp_dir
from ...constants import get_root
from ...git import get_git_email, get_git_user, get_latest_commit_hash
from ..console import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting, echo_warning, run_or_abort

PRODUCTION_BRANCH = 'gh-pages'


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Deploy built documentation')
@click.argument('branch', required=False)
@click.option('--yes', '-y', is_flag=True)
@click.pass_context
def deploy(ctx, branch, yes):
    """Deploy built documentation."""
    # We allow specifying a branch in case you want to quickly showcase changes to others
    # In that case, you should ship them the zip archive linked to at the end of the script.
    if not branch:
        branch = PRODUCTION_BRANCH

    github_token = ctx.obj['github'].get('token')
    if not github_token:
        abort('No `github.token` has been set')

    site_dir = path_join(get_root(), 'site')
    if not dir_exists(site_dir):
        abort('Site directory does not exist, build docs by running `ddev docs build`')

    echo_waiting('Reading current Git configuration...')
    git_user = get_git_user()
    git_email = get_git_email()
    latest_commit_hash = get_latest_commit_hash()
    repo_name = ctx.obj['repo_name']

    if 'GITHUB_ACTIONS' in os.environ:
        remote = f'https://{os.getenv("GITHUB_ACTOR")}:{github_token}@github.com/DataDog/{repo_name}.git'
    else:
        remote = f'https://{github_token}@github.com/DataDog/{repo_name}.git'

    echo_waiting('Copying site to a temporary directory...')
    with temp_dir() as d:
        temp_repo_dir = copy_path(site_dir, d)

        # https://help.github.com/en/github/working-with-github-pages/about-github-pages#static-site-generators
        # https://github.com/mkdocs/mkdocs/pull/2060
        echo_waiting('Writing .nojekyll at the root...')
        create_file(path_join(temp_repo_dir, '.nojekyll'))

        with chdir(temp_repo_dir):
            echo_waiting('Configuring the temporary Git repository...')
            run_or_abort('git init', capture=True)
            run_or_abort(f'git config user.name "{git_user}"', capture=True)
            run_or_abort(f'git config user.email "{git_email}"', capture=True)
            run_or_abort(f'git remote add upstream {remote}', capture=True)

            echo_waiting('Discovering remote...')
            run_or_abort('git fetch --depth 1 upstream', capture=True)

            upstream_check = run_or_abort(f'git ls-remote --heads {remote} {branch}', capture=True)
            if upstream_check.stdout.strip():
                run_or_abort(f'git reset upstream/{branch}', capture=True)

            echo_waiting(f'Committing site contents to branch {branch}...')
            run_or_abort('git add --all', capture=True)

            # If no changes, degrade gracefully
            result = run_or_abort(
                f'git commit -m "build docs at {latest_commit_hash}"', capture=True, ignore_exit_code=True
            )
            if result.code:
                if 'nothing to commit' in result.stdout:
                    echo_warning('No documentation changes, skipping deployment.')
                    abort(code=0)
                else:
                    abort(result.stdout + result.stderr, code=result.code)

            if branch == PRODUCTION_BRANCH and not yes and not click.confirm('Do you want to continue?'):
                abort('Will not deploy')

            run_or_abort(f'git push upstream HEAD:{branch}', capture=True)

    echo_success('Success!')

    if branch != PRODUCTION_BRANCH:
        echo_info(f'Download the site here: https://github.com/DataDog/{repo_name}/archive/{branch}.zip')
