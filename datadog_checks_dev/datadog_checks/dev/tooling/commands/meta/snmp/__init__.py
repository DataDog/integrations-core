# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...console import CONTEXT_SETTINGS
from .generate_profile import generate_profile_from_mibs
from .translate_profile import translate_profile
from .validate_mib_filenames import validate_mib_filenames
from .validate_snmp_profiles import validate_profile

ALL_COMMANDS = [generate_profile_from_mibs, translate_profile, validate_mib_filenames, validate_profile]


@click.group(context_settings=CONTEXT_SETTINGS, short_help='SNMP utilities')
def snmp():
    pass


for command in ALL_COMMANDS:
    snmp.add_command(command)
