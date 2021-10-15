# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
import markdown
from bs4 import BeautifulSoup

from ...annotations import annotate_display_queue
from ...constants import get_root
from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_readme_file, read_readme_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

IMAGE_EXTENSIONS = {".png", ".jpg"}


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate README.md files')
@click.pass_context
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def readmes(ctx, check):
    """Validates README files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """

    repo = ctx.obj['repo_name']

    files_failed = {}
    readme_counter = set()

    integrations = process_checks_option(check, source='integrations', extend_changed=True)

    for integration in integrations:
        display_queue = []
        readme_path = get_readme_file(integration)

        # Validate the README itself
        validate_readme(integration, repo, display_queue, files_failed, readme_counter)

        if display_queue:
            annotate_display_queue(readme_path, display_queue)
            echo_info(f'{integration}:')
            for func, message in display_queue:
                func(message)

    num_files = len(readme_counter)
    files_failed = len(files_failed)
    files_passed = num_files - files_failed

    if files_failed:
        click.echo()
        echo_failure(f'Files with errors: {files_failed}')

    if files_passed:
        if files_failed:
            echo_success(f'Files valid: {files_passed}')
        else:
            echo_success(f'All {len(readme_counter)} READMEs are valid!')

    if files_failed:
        abort()


def validate_readme(integration, repo, display_queue, files_failed, readme_counter):
    readme_path = get_readme_file(integration)
    html = markdown.markdown(read_readme_file(integration))
    soup = BeautifulSoup(html, features="html.parser")
    readme_counter.add(readme_path)

    # Check all required headers are present
    h2s = [h2.text for h2 in soup.find_all("h2")]
    if "Overview" not in h2s or "Setup" not in h2s:
        files_failed[readme_path] = True
        display_queue.append((echo_failure, "     readme is missing either an Overview or Setup H2 (##) section"))

    if "Support" not in h2s and repo == 'marketplace':
        files_failed[readme_path] = True
        display_queue.append((echo_failure, "     readme is missing a Support H2 (##) section"))

    # Check all referenced images are in the `images` folder and that
    # they use the `raw.githubusercontent` format or relative paths to the `images` folder
    allow_relative = False
    if repo == "marketplace":
        allow_relative = True
    img_srcs = [img.attrs.get("src") for img in soup.find_all("img")]
    for img_src in img_srcs:
        image_name = os.path.split(img_src)[-1]
        file_path = os.path.join(get_root(), integration, "images", image_name)
        if img_src.startswith("https://raw.githubusercontent") or (img_src.startswith("images/") and allow_relative):
            if not os.path.exists(file_path):
                files_failed[readme_path] = True
                display_queue.append(
                    (echo_failure, f"     image: {img_src} is linked in its readme but does not exist")
                )
        else:
            error_msg = (
                f"     All images must be checked into the repo under the `{integration}/images` folder. "
                f"This image path must be in the form: "
                f"https://raw.githubusercontent.com/DataDog/{repo}/master/{integration}/images/<IMAGE_NAME>"
            )
            if allow_relative:
                error_msg += "or be a relative path to the `images/` folder (without a `/` prefix)."
            error_msg += f" Image currently is: {img_src}"

            display_queue.append((echo_failure, error_msg))
