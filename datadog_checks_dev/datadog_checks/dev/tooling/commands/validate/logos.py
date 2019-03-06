# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from PIL import Image


from ...constants import NOT_TILES, get_root
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_success, echo_waiting
from ...utils import get_valid_integrations


REQUIRED_IMAGES = {
    'avatars-bot.png': (128, 128),
    'saas_logos-bot.png': (200, 128),
    'saas_logos-small.png': (120, 60)
}


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate logos files'
)
@click.argument('check', required=False)
def logos(check):

    """Validate logo files."""

    if check:
        checks = [check]
    else:
        checks = sorted(get_valid_integrations())

    blacklisted_integrations_msg = ''
    count_successful = 0
    errors = dict()
    error_checks = set()

    for check in checks:
        if check in NOT_TILES:
            blacklisted_integrations_msg += 'Check {} is a blacklisted integration.\n'.format(check)
            continue

        path_to_check_logos = os.path.join(get_root(), check, 'logos')

        for logo, required_size in REQUIRED_IMAGES.items():
            logo_file_name = os.path.join(path_to_check_logos, logo)
            if not os.path.isfile(logo_file_name):
                errors[logo] = '    {} is missing for {}'.format(logo, check)
            else:
                width, height = get_resolution(logo_file_name)
                if (width, height) != required_size:
                    errors[logo] = '    {} has improper resolution: {}. Should be {}'.format(
                        logo, (width, height), required_size
                    )

        if errors.get(logo):
            echo_waiting('{}:'.format(check))
            echo_failure('\n'.join(errors.values()))
            error_checks.add(check)

            errors = dict()
        else:
            count_successful += 1

        if len(checks) == 1 and check not in error_checks:
            echo_waiting('Validating {}... '.format(check), nl=False)
            echo_success('success! :)')

    if not error_checks:
        if len(checks) == 1:
            echo_success('Congrats, all {} logos are valid!'.format(check))
        else:
            echo_success('Congrats, all {} check\'s logo files are valid!'.format(count_successful))
    else:
        echo_success(blacklisted_integrations_msg)
        abort()


def get_resolution(path):
    try:
        with Image.open(path) as logo:
            return logo.size
    except IOError:
        return 0, 0
