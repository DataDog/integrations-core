# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from PIL import Image

from ...constants import get_root
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting


REQUIRED_IMAGES = {
    'avatars-bot.png': (128, 128),
    'saas_logos-bot.png': (200, 128),
    'saas_logos-small.png': (120, 60)
}


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate logos files'
)
@click.argument('check')
def logos(check):
    """Validate logo files."""

    path_to_check_logos = os.path.join(get_root(), check, 'logos')

    echo_info('Validating logos for {}'.format(path_to_check_logos))
    errors = {}

    for logo in REQUIRED_IMAGES:
        echo_waiting('Validating {} file...'.format(logo), nl=False)
        logo_file_name = os.path.join(path_to_check_logos, logo)
        if not os.path.isfile(logo_file_name):
            errors[logo] = '{} is missing for {}'.format(logo, check)
        elif not get_resolution(logo_file_name) == REQUIRED_IMAGES[logo]:
            errors[logo] = '{} has improper resolution: {}. Should be {}'.format(logo, (width, height), REQUIRED_IMAGES[logo])

        if errors.get(logo):
            echo_failure(errors[logo])
        else:
            echo_info('done')

    if errors:
        abort(text='Validation of {} logos failed. See above errors'.format(check))
    else:
        echo_success('Congrats, all {} logos are valid!'.format(check))


def get_resolution(path):
    try:
        with Image.open(path) as logo:
            return logo.size
    except IOError:
        return 0, 0
