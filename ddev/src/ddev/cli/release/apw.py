# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Package and publish the source snapshots consumed by APW."""

import json
import os
from pathlib import Path

import click

from ddev.release.apw import Release, package


@click.command(short_help="Package, check, tag, or publish an APW source snapshot")
@click.argument('action', type=click.Choice(['package', 'check', 'tag', 'publish']))
@click.option('--repository', required=True, envvar=['GH_REPO', 'GITHUB_REPOSITORY'], help='GitHub owner/repository.')
@click.option('--commit', required=True, help='Full lowercase source commit SHA.')
@click.option('--source', type=click.Path(path_type=Path, exists=True, file_okay=False), default='.', show_default=True)
@click.option('--directory', type=click.Path(path_type=Path, file_okay=False), default='dist', show_default=True)
@click.option('--exclude', multiple=True, help='Package only: repo-relative Git glob to exclude. May be repeated.')
def apw(action: str, repository: str, commit: str, source: Path, directory: Path, exclude: tuple[str, ...]) -> None:
    """Create deterministic source archives and immutable apw-assets-<commit> prereleases.

    Run with `ddev --here` from any asset checkout, including ddoghq repositories;
    no integration metadata or ddev repository alias is required. Package reads
    Git objects, not uncommitted files. Exclusions are owned by each producer;
    APW selects the actual asset types downstream.

    Check prints package=true/false for GITHUB_OUTPUT, verifying an existing
    release before skipping. Publish requires gh authentication and the GitHub
    Actions GITHUB_SERVER_URL/GITHUB_RUN_ID environment for provenance. It
    resumes matching drafts and never replaces existing uploads.

    Tag creates the source tag using the current gh credentials. Workflows use
    Octo STS for this step, then GITHUB_TOKEN for publish so the release author
    and asset uploader remain github-actions[bot] for APW pin approval.
    """
    if exclude and action != 'package':
        raise click.UsageError('--exclude only applies to package')
    try:
        release = Release(repository, commit)
        if action == 'package':
            click.echo(json.dumps(package(source, repository, commit, directory, exclude), indent=2))
            return
        if action == 'check':
            needed = release.needs_package()
            click.echo(f'package={str(needed).lower()}')
            message = 'Packaging needed.' if needed else 'Complete release exists; skipping packaging and publication.'
        elif action == 'tag':
            message = release.ensure_tag()
        else:
            message = release.publish(directory)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f'{release.tag}: {message}', err=True)
    if summary := os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(summary, 'a') as output:
            output.write(f'{message}\n\nCommit: `{release.commit}`\n')
