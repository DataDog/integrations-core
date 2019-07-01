# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from PIL import Image

from ...constants import NOT_TILES, get_root
from ...utils import get_valid_integrations, load_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting

REQUIRED_IMAGES = {'avatars-bot.png': (128, 128), 'saas_logos-bot.png': (200, 128), 'saas_logos-small.png': (120, 60)}


@click.command(
    context_settings=CONTEXT_SETTINGS, short_help='Validate logos files, specifying no check will validate all logos'
)
@click.argument('check', required=False)
def logos(check):

    """Validate logo files. Specifying no check will validate all logos"""

    valid_checks = get_valid_integrations()
    if check:
        if check in valid_checks:
            checks = [check]
        else:
            echo_info('{} is not an integration.'.format(check))
            return
    else:
        checks = sorted(valid_checks)

    blacklisted_integrations_msg = ''
    count_successful = 0
    error_checks = set()

    for check in checks:
        errors = dict()
        display_name = load_manifest(check).get('display_name', check)
        if check in NOT_TILES:
            blacklisted_integrations_msg += '{} does not currently have an integration tile.\n'.format(display_name)
            continue

        path_to_check_logos = os.path.join(get_root(), check, 'assets', 'logos')

        for logo, required_size in REQUIRED_IMAGES.items():
            logo_file_name = os.path.join(path_to_check_logos, logo)
            if not os.path.isfile(logo_file_name):
                errors[logo] = '    {} is missing for {}'.format(logo, display_name)
            else:
                size = get_resolution(logo_file_name)
                if size != required_size:
                    errors[logo] = '    {} has improper resolution: {}. Should be {}'.format(logo, size, required_size)

        if errors:
            echo_waiting('{}:'.format(display_name))
            echo_failure('\n'.join(errors.values()))
            error_checks.add(check)
        else:
            count_successful += 1

    blacklisted_integrations_msg = blacklisted_integrations_msg.rstrip()

    if error_checks:
        echo_success(blacklisted_integrations_msg)
        abort()
    elif len(checks) == 1:
        if blacklisted_integrations_msg:
            echo_success(blacklisted_integrations_msg)
        else:
            echo_success('Congrats, all {} logos are valid!'.format(display_name))
    else:
        echo_success(
            'Congrats, all {} checks\' logo files are valid! {} checks were blacklisted and skipped.'.format(
                count_successful, len(NOT_TILES)
            )
        )


def get_resolution(path):
    try:
        with Image.open(path) as logo:
            return logo.size
    except IOError:
        return 0, 0
