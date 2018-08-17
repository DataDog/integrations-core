# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import uuid
from collections import defaultdict
from datetime import datetime

import click

from .utils import CONTEXT_SETTINGS, abort, echo_info, echo_success
from ..constants import get_root
from ..create import create_template_files, get_valid_templates
from ..utils import normalize_package_name
from ...utils import resolve_path

HYPHEN = b'\xe2\x94\x80\xe2\x94\x80'.decode('utf-8')
PIPE = b'\xe2\x94\x82'.decode('utf-8')
PIPE_MIDDLE = b'\xe2\x94\x9c'.decode('utf-8')
PIPE_END = b'\xe2\x94\x94'.decode('utf-8')


def tree():
    return defaultdict(tree)


def construct_output_info(path, depth, last, is_dir=False):
    if depth == 0:
        return u'', path, is_dir
    else:
        if depth == 1:
            return (
                u'{}{} '.format(
                    PIPE_END if last else PIPE_MIDDLE, HYPHEN
                ),
                path,
                is_dir
            )
        else:
            return (
                u'{}   {}{}'.format(
                    PIPE,
                    u' ' * 4 * (depth - 2),
                    u'{}{} '.format(PIPE_END if last or is_dir else PIPE_MIDDLE, HYPHEN)
                ),
                path,
                is_dir
            )


def path_tree_output(path_tree, depth=0):
    # Avoid possible imposed recursion limits by using a generator.
    # See https://en.wikipedia.org/wiki/Trampoline_(computing)
    dirs = []
    files = []

    for path in path_tree:
        if len(path_tree[path]) > 0:
            dirs.append(path)
        else:
            files.append(path)

    dirs.sort()
    length = len(dirs)

    for i, path in enumerate(dirs, 1):
        yield construct_output_info(path, depth, last=i == length and not files, is_dir=True)

        for info in path_tree_output(path_tree[path], depth + 1):
            yield info

    files.sort()
    length = len(files)

    for i, path in enumerate(files, 1):
        yield construct_output_info(path, depth, last=i == length)


def display_path_tree(path_tree):
    for indent, path, is_dir in path_tree_output(path_tree):
        if indent:
            echo_info(indent, nl=False)

        if is_dir:
            echo_success(path)
        else:
            echo_info(path)


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Create scaffolding for a new integration')
@click.argument('name')
@click.option(
    '--type', '-t', 'integration_type',
    type=click.Choice(get_valid_templates()),
    default='check',
    help='The type of integration to create'
)
@click.option('--location', '-l', help='Where to create the integration')
@click.option('--quiet', '-q', is_flag=True, help='Show less output')
@click.option('--dry-run', '-n', is_flag=True, help='Only show what would be created')
@click.pass_context
def create(ctx, name, integration_type, location, quiet, dry_run):
    """Create scaffolding for a new integration."""
    integration_name = normalize_package_name(name)
    root = resolve_path(location) if location else get_root()
    path_sep = os.path.sep

    integration_dir = os.path.join(root, integration_name)
    if os.path.exists(integration_dir):
        abort('Path `{}` already exists!'.format(integration_dir))

    check_name_cap = integration_name if integration_name.count('_') else integration_name.capitalize()
    repo_choice = ctx.obj['repo_choice']
    if repo_choice == 'core':
        author = 'Datadog'
        email = 'help@datadoghq.com'
        email_packages = 'packages@datadoghq.com'
        install_info = (
            'The {} check is included in the [Datadog Agent][2] package, so you do not\n'
            'need to install anything else on your server.'.format(check_name_cap)
        )
        support_type = 'core'
        tox_base_dep = '../datadog_checks_base[deps]'
    else:
        author = 'U.N. Owen'
        email = email_packages = 'friend@datadog.community'
        install_info = (
            'The {} check is not included in the [Datadog Agent][2] package, so you will\n'
            'need to install it yourself.'.format(check_name_cap)
        )
        support_type = 'contrib'
        tox_base_dep = 'datadog-checks-base[deps]'

    config = {
        'author': author,
        'check_class': '{}Check'.format(''.join(part.capitalize() for part in integration_name.split('_'))),
        'check_name': integration_name,
        'check_name_cap': check_name_cap,
        'email': email,
        'email_packages': email_packages,
        'guid': uuid.uuid4(),
        'install_info': install_info,
        'repo_choice': repo_choice,
        'support_type': support_type,
        'tox_base_dep': tox_base_dep,
        'year': str(datetime.now().year),
    }

    files = create_template_files(integration_type, root, config, read=not dry_run)
    file_paths = [file.file_path.replace('{}{}'.format(root, path_sep), '', 1) for file in files]

    path_tree = tree()
    for file_path in file_paths:
        branch = path_tree

        for part in file_path.split(path_sep):
            branch = branch[part]

    if dry_run:
        if quiet:
            echo_info('Will create `{}`'.format(integration_dir))
        else:
            echo_info('Will create in `{}`:'.format(root))
            display_path_tree(path_tree)
        return

    for file in files:
        file.write()

    if quiet:
        echo_info('Created `{}`'.format(integration_dir))
    else:
        echo_info('Created in `{}`:'.format(root))
        display_path_tree(path_tree)
