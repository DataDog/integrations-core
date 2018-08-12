# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import defaultdict

import click

from .utils import CONTEXT_SETTINGS, abort, echo_info, echo_success
from ..constants import get_root
from ..files import CHECK_FILES
from ..utils import normalize_package_name

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


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Create a new integration')
@click.argument('name')
@click.option('--dry-run', '-n', is_flag=True, help='Only show what would be created')
@click.pass_context
def create(ctx, name, dry_run):
    """Create a new integration."""
    check_name = normalize_package_name(name)
    root = get_root()
    path_sep = os.path.sep

    check_dir = os.path.join(root, check_name)
    if os.path.exists(check_dir):
        abort('Path `{}` already exists!'.format(check_dir))

    config = {
        'root': check_dir,
        'check_name': check_name,
        'check_name_cap': check_name.capitalize(),
        'check_class': '{}Check'.format(''.join(part.capitalize() for part in check_name.split('_'))),
        'repo_choice': ctx.obj['repo_choice'],
    }

    files = [file(config) for file in CHECK_FILES]
    file_paths = [file.file_path.replace('{}{}'.format(root, path_sep), '', 1) for file in files]

    path_tree = tree()
    for file_path in file_paths:
        branch = path_tree

        for part in file_path.split(path_sep):
            branch = branch[part]

    if dry_run:
        echo_info('Will create in `{}`:'.format(root))
        display_path_tree(path_tree)
        return

    for file in files:
        file.write()

    echo_info('Created in `{}`:'.format(root))
    display_path_tree(path_tree)
