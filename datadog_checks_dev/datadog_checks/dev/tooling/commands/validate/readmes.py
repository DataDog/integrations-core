# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from os import path

import click

from ...utils import complete_valid_checks, get_root, get_valid_integrations, read_readme_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

IMAGE_EXTENSIONS = {".png", ".jpg"}


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate README.md files')
@click.pass_context
@click.argument('integration', autocompletion=complete_valid_checks, required=False)
def readmes(ctx, integration):
    """Validates README files

    If `check` is specified, only the check will be validated,
    otherwise all README files in the repo will be.
    """

    repo = ctx.obj['repo_name']
    integrations = []
    failed_checks = 0

    if integration:
        integrations = [integration]
    else:
        integrations = sorted(get_valid_integrations())

    for integration in integrations:
        has_overview = False
        has_setup = False
        errors = False
        display_queue = []

        lines = read_readme_file(integration)
        for line_no, line in lines:

            if "## Overview" == line.strip():
                has_overview = True

            if "## Setup" == line.strip():
                has_setup = True

            for ext in IMAGE_EXTENSIONS:
                if ext in line:
                    IMAGE_REGEX = (
                        rf".*https:\/\/raw\.githubusercontent\.com\/DataDog\/"
                        rf"{re.escape(repo)}\/master\/({re.escape(integration)}\/images\/.*.{ext}).*"
                    )

                    match = re.match(IMAGE_REGEX, line)
                    if not match:
                        errors = True
                        display_queue.append((echo_failure, f"     No valid image file on line {line_no}"))
                        display_queue.append(
                            (
                                echo_info,
                                f"     This image path must be in the form: "
                                f"https://raw.githubusercontent.com/DataDog/{repo}/master/{integration}/images/<IMAGE_NAME>",  # noqa
                            )
                        )
                        break

                    rel_path = match.groups()[0]
                    if rel_path:
                        file_path = path.join(get_root(), rel_path)
                        if not path.exists(file_path):
                            errors = True
                            display_queue.append(
                                (echo_failure, f"     image: {rel_path} is linked in its readme but does not exist")
                            )

        if not (has_overview and has_setup):
            errors = True
            display_queue.append((echo_failure, "     readme does not contain both an Overview and Setup H2 section"))

        if errors:
            failed_checks += 1
            echo_info(f"{integration}/README.md... ", nl=False)
            echo_failure("FAILED")
            for display_func, message in display_queue:
                display_func(message)

    if failed_checks:
        echo_failure(f"{failed_checks} invalid files")
        abort()
    else:
        echo_success("All READMEs are valid!")
