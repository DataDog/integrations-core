# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import defaultdict

import click

from ...fs import resolve_path
from ..constants import get_root
from ..create import construct_template_fields, create_template_files, get_valid_templates
from ..utils import kebab_case_name, normalize_package_name
from .console import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_warning

HYPHEN = b'\xe2\x94\x80\xe2\x94\x80'.decode('utf-8')
PIPE = b'\xe2\x94\x82'.decode('utf-8')
PIPE_MIDDLE = b'\xe2\x94\x9c'.decode('utf-8')
PIPE_END = b'\xe2\x94\x94'.decode('utf-8')


def tree():
    return defaultdict(tree)


def construct_output_info(path, depth, last, is_dir=False):
    if depth == 0:
        return '', path, is_dir
    else:
        if depth == 1:
            return (f'{PIPE_END if last else PIPE_MIDDLE}{HYPHEN} ', path, is_dir)
        else:
            return (
                f"{PIPE}   {' ' * 4 * (depth - 2)}{PIPE_END if last or is_dir else PIPE_MIDDLE}{HYPHEN} ",
                path,
                is_dir,
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
    '--type',
    '-t',
    'integration_type',
    type=click.Choice(get_valid_templates()),
    default='check',
    help='The type of integration to create',
)
@click.option('--location', '-l', help='The directory where files will be written')
@click.option('--non-interactive', '-ni', is_flag=True, help='Disable prompting for fields')
@click.option('--quiet', '-q', is_flag=True, help='Show less output')
@click.option('--dry-run', '-n', is_flag=True, help='Only show what would be created')
@click.pass_context
def create(ctx, name, integration_type, location, non_interactive, quiet, dry_run):
    """
    Create scaffolding for a new integration.

    NAME: The display name of the integration that will appear in documentation.
    """

    if name.islower():
        echo_warning('Make sure to use the display name. e.g. MapR, Ambari, IBM MQ, vSphere, ...')

    repo_choice = ctx.obj['repo_choice']
    root = resolve_path(location) if location else get_root()
    path_sep = os.path.sep

    integration_dir_name = normalize_package_name(name)
    if integration_type == 'snmp_tile':
        integration_dir_name = 'snmp_' + integration_dir_name
    integration_dir = os.path.join(root, integration_dir_name)
    if os.path.exists(integration_dir):
        abort(f'Path `{integration_dir}` already exists!')

    template_fields = {}
    if non_interactive and repo_choice != 'core':
        abort(f'Cannot use non-interactive mode with repo_choice: {repo_choice}')

    if not non_interactive and not dry_run:
        if repo_choice != 'core':
            template_fields['email'] = click.prompt('Email used for support requests')
            template_fields['email_packages'] = template_fields['email']
        if repo_choice == 'extras':
            template_fields['author'] = click.prompt('Your name')

        if repo_choice == 'marketplace':
            author_name = click.prompt('Your Company Name')
            homepage = click.prompt('The product or company homepage')
            template_fields['author'] = author_name
            template_fields[
                'author_info'
            ] = f'\n  "author": {{\n    "name": "{author_name}",\n    "homepage": "{homepage}"\n  }},'

            eula = 'assets/eula.pdf'
            legal_email = click.prompt('The Legal email used to receive subscription notifications')
            template_fields[
                'terms'
            ] = f'\n  "terms": {{\n    "eula": "{eula}",\n    "legal_email": "{legal_email}"\n  }},'

            template_fields['pricing_plan'] = '\n  "pricing": [],'

            template_fields['integration_id'] = f'{kebab_case_name(author_name)}-{kebab_case_name(name)}'

            template_fields['package_url'] = ''
        else:
            # Fill in all common non Marketplace fields
            template_fields['pricing_plan'] = ''
            template_fields['author_info'] = ''
            template_fields['terms'] = ''
            template_fields['integration_id'] = kebab_case_name(name)
            template_fields['package_url'] = (
                f"\n    # The project's main homepage."
                f"\n    url='https://github.com/DataDog/integrations-{repo_choice}',"
            )
    config = construct_template_fields(name, repo_choice, **template_fields)

    files = create_template_files(integration_type, root, config, read=not dry_run)
    file_paths = [file.file_path.replace(f'{root}{path_sep}', '', 1) for file in files]

    path_tree = tree()
    for file_path in file_paths:
        branch = path_tree

        for part in file_path.split(path_sep):
            branch = branch[part]

    if dry_run:
        if quiet:
            echo_info(f'Will create `{integration_dir}`')
        else:
            echo_info(f'Will create in `{root}`:')
            display_path_tree(path_tree)
        return

    for file in files:
        file.write()

    if quiet:
        echo_info(f'Created `{integration_dir}`')
    else:
        echo_info(f'Created in `{root}`:')
        display_path_tree(path_tree)
