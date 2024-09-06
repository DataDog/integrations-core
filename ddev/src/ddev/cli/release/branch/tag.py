import re

import click
from packaging.version import Version

from .create import BRANCH_NAME_REGEX


@click.command
@click.option(
    '--final/--rc',
    default=False,
    show_default=True,
    help="Whether we're tagging the final release or a release candidate (rc).",
)
@click.pass_obj
def tag(app, final):
    """
    Tag the release branch either as release candidate or final release.
    """
    branch_name = app.repo.git.current_branch()
    release_branch = BRANCH_NAME_REGEX.match(branch_name)
    if release_branch is None:
        app.abort(
            f'Invalid branch name: {branch_name}. Branch name must match the pattern {BRANCH_NAME_REGEX.pattern}.'
        )
    click.echo(app.repo.git.pull(branch_name))
    click.echo(app.repo.git.fetch_tags())
    major_minor_version = branch_name.replace('.x', '')
    this_release_tags = sorted(
        (
            Version(t)
            for t in set(app.repo.git.tags(glob_pattern=major_minor_version + '.*'))
            # We take 'major.minor.x' as the branch name pattern and replace 'x' with 'patch-rc.number'.
            # We make the RC component optional so that final tags also match our filter.
            if re.match(BRANCH_NAME_REGEX.pattern.replace('x', r'\d+(\-rc\.\d+)?'), t)
        ),
        reverse=True,
    )
    last_patch, last_rc = _extract_patch_and_rc(this_release_tags)
    last_tag_was_final = last_rc is None
    new_patch = last_patch + 1 if last_tag_was_final else last_patch
    new_tag = f'{major_minor_version}.{new_patch}'
    if not final:
        new_rc_guess = 1 if last_tag_was_final else last_rc + 1
        next_rc = click.prompt(
            'What RC number are we tagging? (hit ENTER to accept suggestion)', type=int, default=new_rc_guess
        )
        if next_rc < 1:
            app.abort('RC number must be at least 1.')
        new_tag += f'-rc.{next_rc}'
        if Version(new_tag) in this_release_tags:
            app.abort(f'Tag {new_tag} already exists. Switch to git to overwrite it.')
        if not last_tag_was_final and next_rc < last_rc:
            click.secho('!!! WARNING !!!')
            if not click.confirm(
                f'The latest RC is {last_rc}. '
                'You are about to go back in time by creating an RC with a number less than that. Are you sure? [y/N]'
            ):
                app.abort('Did not get confirmation, aborting. Did not create or push the tag.')
    if not click.confirm(f'Create and push this tag: {new_tag}?'):
        app.abort('Did not get confirmation, aborting. Did not create or push the tag.')
    click.echo(app.repo.git.tag(new_tag, message=new_tag))
    click.echo(app.repo.git.push(new_tag))


def _extract_patch_and_rc(version_tags):
    if not version_tags:
        return 0, 0
    latest = version_tags[0]
    patch = latest.micro
    # latest.pre is None for final releases and a tuple ('rc', <NUM>) for RC.
    rc = latest.pre if latest.pre is None else latest.pre[1]
    return patch, rc
