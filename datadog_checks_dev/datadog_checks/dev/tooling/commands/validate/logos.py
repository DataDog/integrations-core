# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from PIL import Image

from ...constants import NOT_TILES, get_root
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_success, echo_waiting
from ...utils import get_valid_tile_checks


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
        if check in NOT_TILES:
            echo_success(text='Check {} is a blacklisted integration.'.format(check))
            return
        else:
            checks = [check]
    else:
        checks = sorted(get_valid_tile_checks())

    errors = dict()
    error_checks = set()

    for check in checks:
        path_to_check_logos = os.path.join(get_root(), check, 'logos')

        for logo, required_size in REQUIRED_IMAGES.items():
            # echo_waiting('Validating {} file...'.format(logo), nl=False)
            logo_file_name = os.path.join(path_to_check_logos, logo)
            if not os.path.isfile(logo_file_name):
                errors[logo] = '{} is missing for {}'.format(logo, check)
            else:
                width, height = get_resolution(logo_file_name)
                if not (width, height) == required_size:
                    errors[logo] = '{} has improper resolution: {}. Should be {}'.format(
                        logo, (width, height), required_size
                    )

            if errors.get(logo):
                echo_waiting('Validation of {} for {} failed'.format(logo, check))
                echo_failure(errors[logo])
                error_checks.add(check)

            errors = dict()

        if check not in error_checks:
            echo_waiting('Validating {}...'.format(check), nl=False)
            echo_success('Success')

    if error_checks:
        error_checks_string = ', '.join((e for e in sorted(error_checks)))
        abort(
            text='Validation of {} logos failed. See above errors'.format(error_checks_string)
        )
    else:
        echo_success('Congrats, all {} logos are valid!'.format('' if len(checks) > 1 else check))


def get_resolution(path):
    try:
        with Image.open(path) as logo:
            return logo.size
    except IOError:
        return 0, 0
