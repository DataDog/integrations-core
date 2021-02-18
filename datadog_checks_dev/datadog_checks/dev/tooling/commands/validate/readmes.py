# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from os import path

import click

from datadog_checks.dev.tooling.specs.docs import DocsSpec
from datadog_checks.dev.tooling.specs.docs.consumers import ReadmeConsumer

from ....utils import file_exists, path_join, read_file, write_file
from ...utils import (
    complete_valid_checks,
    get_check_package_directory,
    get_docs_spec,
    get_readme_file,
    get_root,
    get_valid_integrations,
    get_version_string,
    load_manifest,
    read_readme_file,
)
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning

IMAGE_EXTENSIONS = {".png", ".jpg"}


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate README.md files')
@click.pass_context
@click.argument('integration', autocompletion=complete_valid_checks, required=False)
@click.option('--sync', '-s', is_flag=True, help='Generate README files based on specifications')
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
def readmes(ctx, integration, sync, verbose):
    """Validates README files

    If `check` is specified, only the check will be validated,
    otherwise all README files in the repo will be.
    """

    repo = ctx.obj['repo_name']

    files_failed = {}
    files_warned = {}
    spec_counter = []
    readme_counter = set()

    if integration:
        integrations = [integration]
    else:
        integrations = sorted(get_valid_integrations())

    for integration in integrations:
        display_queue = []
        manifest = load_manifest(integration)

        # If we have a spec, then validate and optionally sync it
        spec_path = get_docs_spec(integration)
        if file_exists(spec_path):
            spec_counter.append(None)
            display_name = manifest.get('display_name', integration)
            source = integration
            version = get_version_string(integration)

            spec = DocsSpec(read_file(spec_path), source=source, version=version)
            spec.load()

            if spec.errors:
                files_failed[spec_path] = True
                for error in spec.errors:
                    display_queue.append(lambda error=error, **kwargs: echo_failure(error, **kwargs))
            else:
                if spec.data['name'] != display_name:
                    files_failed[spec_path] = True
                    display_queue.append(
                        lambda **kwargs: echo_failure(
                            f"Spec  name `{spec.data['name']}` should be `{display_name}`", **kwargs
                        )
                    )

                readme_location = get_check_package_directory(integration)
                readme_consumer = ReadmeConsumer(spec.data)
                for readme_file, (contents, errors) in readme_consumer.render().items():
                    readme_file_path = path_join(readme_location, readme_file)
                    readme_counter.add(readme_file_path)
                    if errors:
                        files_failed[readme_file_path] = True
                        for error in errors:
                            display_queue.append(lambda error=error, **kwargs: echo_failure(error, **kwargs))
                    else:
                        if not file_exists(readme_file_path) or read_file(readme_file_path) != contents:
                            if sync:
                                echo_info(f"Writing README file to `{readme_file_path}`")
                                write_file(readme_file_path, contents)
                            else:
                                files_failed[readme_file_path] = True
                                display_queue.append(
                                    lambda readme_file=readme_file, **kwargs: echo_failure(
                                        f'File `{readme_file}` is not in sync, run "ddev validate readmes -s"', **kwargs
                                    )
                                )

        # Validate the README itself
        validate_readme(integration, repo, manifest, display_queue, files_failed, readme_counter)

        if display_queue or verbose:
            echo_info(f'{integration}:')
            if verbose:
                display_queue.append(lambda **kwargs: echo_info('Valid spec', **kwargs))
            for display in display_queue:
                display(indent=True)

    num_files = len(spec_counter) + len(readme_counter)
    files_failed = len(files_failed)
    files_warned = len(files_warned)
    files_passed = num_files - (files_failed + files_warned)

    if files_failed or files_warned:
        click.echo()

    if files_failed:
        echo_failure(f'Files with errors: {files_failed}')

    if files_warned:
        echo_warning(f'Files with warnings: {files_warned}')

    if files_passed:
        if files_failed or files_warned:
            echo_success(f'Files valid: {files_passed}')
        else:
            if spec_counter:
                echo_success(f'All {len(spec_counter)} documentation specs are valid!')
            echo_success(f'All {len(readme_counter)} READMEs are valid!')

    if files_failed:
        abort()


def validate_readme(integration, repo, manifest, display_queue, files_failed, readme_counter):
    has_overview = False
    has_setup = False
    has_support = False

    readme_path = get_readme_file(integration)
    lines = read_readme_file(integration)
    readme_counter.add(readme_path)

    for line_no, line in lines:

        if "## Overview" == line.strip():
            has_overview = True

        if "## Setup" == line.strip():
            has_setup = True

        if "## Support" == line.strip():
            has_support = True

        for ext in IMAGE_EXTENSIONS:
            if ext in line:
                IMAGE_REGEX = (
                    rf".*https:\/\/raw\.githubusercontent\.com\/DataDog\/"
                    rf"{re.escape(repo)}\/master\/({re.escape(integration)}\/images\/.*.{ext}).*"
                )

                match = re.match(IMAGE_REGEX, line)
                if not match:
                    files_failed[readme_path] = True
                    display_queue.append(
                        lambda line_no=line_no, **kwargs: echo_failure(
                            f"     No valid image file on line {line_no}", **kwargs
                        )
                    )
                    display_queue.append(
                        lambda repo=repo, integration=integration, **kwargs: echo_failure(
                            f"     This image path must be in the form: "
                            f"https://raw.githubusercontent.com/DataDog/{repo}/master/{integration}/images/<IMAGE_NAME>",  # noqa
                            **kwargs,
                        )
                    )
                    break

                rel_path = match.groups()[0]
                if rel_path:
                    file_path = path.join(get_root(), rel_path)
                    if not path.exists(file_path):
                        files_failed[readme_path] = True
                        display_queue.append(
                            lambda rel_path=rel_path, **kwargs: echo_failure(
                                f"     image: {rel_path} is linked in its readme but does not exist", **kwargs
                            )
                        )
    if not has_support and manifest.get('support') == 'partner':
        files_failed[readme_path] = True
        display_queue.append(
            lambda **kwargs: echo_failure("     readme does not contain a Support H2 section", **kwargs)
        )

    if not (has_overview and has_setup):
        files_failed[readme_path] = True
        display_queue.append(
            lambda **kwargs: echo_failure(
                "     readme does not contain both an Overview and Setup H2 section", **kwargs
            )
        )
