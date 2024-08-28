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
            if re.match(BRANCH_NAME_REGEX.pattern.replace('x', r'\d+\-rc\.\d+'), t)
        ),
        reverse=True,
    )
    patch_version, next_rc_guess = (
        # The first item in this_release_tags is the latest tag parsed as a Version object.
        (this_release_tags[0].micro, this_release_tags[0].pre[1] + 1)
        if this_release_tags
        else (0, 1)
    )
    if final:
        new_tag = f'{major_minor_version}.{patch_version}'
    else:
        next_rc = click.prompt(
            'What RC number should be tagged? (hit ENTER to accept suggestion)', type=int, default=next_rc_guess
        )
        new_tag = f'{major_minor_version}.{patch_version}-rc.{next_rc}'
        if Version(new_tag) in this_release_tags:
            app.abort(f'Tag {new_tag} already exists. Switch to git to overwrite it.')
        if next_rc < next_rc_guess:
            click.secho('!!! WARNING !!!')
            if not click.confirm(
                'You are about to create an RC with a number less than the latest RC number (12). Are you sure?'
            ):
                app.abort('Did not get confirmation, aborting. Did not create or push the tag.')
    if not click.confirm(f'Create and push this tag: {new_tag}?'):
        app.abort('Did not get confirmation, aborting. Did not create or push the tag.')
    click.echo(app.repo.git.tag(new_tag, message=new_tag))
    click.echo(app.repo.git.push(new_tag))
