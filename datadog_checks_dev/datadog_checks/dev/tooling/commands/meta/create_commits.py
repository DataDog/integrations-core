# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import shutil

import click

from ...constants import get_root
from ...git import get_current_branch, git_commit
from ..console import CONTEXT_SETTINGS, abort, echo_info

"""
This script will create sequential commits on a branch in the specified repo,
to demonstrate the process of building a new integration.

It first checks to make sure the "master" or "main" branches are not active, then proceeds
to copy and commit the contents of each of the folders in this directory.

Argument `source_dir` should be a directory with numbered subdirectories in the order
of commits.  The name of the subdirectory will be the commit message, and the contents
will be committed to the repo on the feature branch in ascending order.

"""


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Create branch commits from example repo')
@click.argument('source_dir')
@click.option('--prefix', '-p', default='', help='Optional text to prefix each commit')
@click.pass_context
def create_example_commits(ctx, source_dir, prefix):
    repo_choice = ctx.obj['repo_choice']
    root = get_root()
    branch = get_current_branch()
    source_dir = os.path.expanduser(source_dir)

    if not os.path.exists(source_dir):
        abort(f'Source directory path `{source_dir}`, not found')

    echo_info(f'Using `{source_dir}` as source directory ...')

    if branch in ('master', 'main'):
        abort(f'Change to a feature branch on `{repo_choice}`, and rerun the command.')

    echo_info(f'Destination repo `{repo_choice}` on branch `{branch}` located at `{root}` ...')

    stages = [x for x in sorted(os.listdir(source_dir)) if x[0].isdigit()]
    echo_info(f"Found the following stages to commit: {', '.join(stages)}")

    for stage in stages:
        base = os.path.join(source_dir, stage)
        targets = []
        for contents in os.listdir(base):
            target = os.path.join(get_root(), contents)
            shutil.copytree(os.path.join(base, contents), target, dirs_exist_ok=True)
            targets.append(target)

        echo_info(f'Committing files from {targets} under commit {stage} ..')
        git_commit(targets, f'{prefix} {stage}')

    echo_info('Done.')
