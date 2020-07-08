# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import click

from ...utils import complete_valid_checks, get_valid_integrations, read_readme_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

IMAGE_EXTENSIONS = {"png", "jpg"}
NON_TILE_INTEGRATIONS = {"sortdb", "hbase_master", "kube_proxy"}

@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate README.md files')
@click.pass_context
@click.argument('integration', autocompletion=complete_valid_checks, required=False)
def readmes(ctx, integration):
    """Validates README files

    If `check` is specified, only the check will be validated,
    otherwise all README files in the repo will be.
    """

    repo = ctx.obj['repo_name']

    errors = False
    integrations = []
    
    if integration:
        integrations = [integration]
    else:
        integrations = sorted(get_valid_integrations())

    for integration in integrations:
        has_overview = False
        has_setup = False

        lines = read_readme_file(integration)
        for line_no, line in lines:
            
            if "## Overview" in line:
                has_overview = True
            
            if "## Setup" in line:
                has_setup = True

            for ext in IMAGE_EXTENSIONS:
                if ext in line:
                    IMAGE_REGEX = (
                        rf".*https:\/\/raw\.githubusercontent\.com\/DataDog\/"
                        rf"{re.escape(repo)}\/master\/{re.escape(integration)}\/images\/.*.\.{ext}.*"
                    )

                    if not re.match(IMAGE_REGEX, line):
                        errors = True
                        echo_failure(f"{integration} readme file does not have a valid image file on line {line_no}")
                        echo_info(
                            f"This image path must be in the form: "
                            f"https://raw.githubusercontent.com/DataDog/{repo}/master/{integration}/images/<IMAGE_NAME>"
                        )
                        continue
                    
        if not has_overview and integration not in NON_TILE_INTEGRATIONS:
            errors = True
            echo_failure(f"{integration} readme file does not have an overview section")
            
        if not has_setup and integration not in NON_TILE_INTEGRATIONS:
            errors = True
            echo_failure(f"{integration} readme file does not have a setup section")

    if errors:
        abort()

    echo_success("All READMEs are valid!")
