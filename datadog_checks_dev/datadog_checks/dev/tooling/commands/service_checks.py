# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import json
from collections import OrderedDict

import click
from six import string_types

from .utils import CONTEXT_SETTINGS, abort, echo_failure, echo_info
from ..constants import get_root
from ...compat import JSONDecodeError
from ...utils import file_exists, read_file

REQUIRED_ATTRIBUTES = {
    'agent_version',
    'check',
    'description',
    'groups',
    'integration',
    'name',
    'statuses',
}


def parse_version_parts(version):
    return (
        [int(v) for v in version.split('.') if v.isdigit()]
        if isinstance(version, string_types) else []
    )


@click.group(
    context_settings=CONTEXT_SETTINGS,
    short_help='Manage service checks files'
)
def service_checks():
    pass


@service_checks.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate all `service_checks.json` files'
)
def verify():
    """Validate all `service_checks.json` files."""

    failed = 0
    root = get_root()

    for check_name in sorted(os.listdir(root)):
        service_checks_file = os.path.join(root, check_name, 'service_checks.json')

        if file_exists(service_checks_file):
            display_queue = [(echo_info, '{} ->'.format(check_name))]

            try:
                decoded = json.loads(read_file(service_checks_file).strip(), object_pairs_hook=OrderedDict)
            except JSONDecodeError:
                failed += 1
                display_queue.append((echo_failure, '  invalid json: {}'.format(service_checks_file)))

                for display, message in display_queue:
                    display(message)
                continue

            unique_names = set()
            unique_checks = set()
            for service_check in decoded:
                # attributes are valid
                attrs = set(service_check)
                for attr in sorted(attrs - REQUIRED_ATTRIBUTES):
                    failed += 1
                    display_queue.append((echo_failure, '  Attribute `{}` is invalid'.format(attr)))
                for attr in sorted(REQUIRED_ATTRIBUTES - attrs):
                    failed += 1
                    display_queue.append((echo_failure, '  Attribute `{}` is required'.format(attr)))

                # agent_version
                agent_version = service_check.get('agent_version')
                version_parts = parse_version_parts(agent_version)
                if len(version_parts) != 3:
                    failed += 1

                    if not agent_version:
                        output = '  required non-null string: agent_version'
                    else:
                        output = '  invalid `agent_version`: {}'.format(agent_version)

                    display_queue.append((echo_failure, output))

                # check
                check = service_check.get('check')
                if not check or not isinstance(check, string_types):
                    failed += 1
                    display_queue.append((echo_failure, '  required non-null string: check'))
                else:
                    if check in unique_checks:
                        failed += 1
                        display_queue.append((echo_failure, '  {} is not a unique check'.format(check)))
                    else:
                        unique_checks.add(check)

                # description
                description = service_check.get('description')
                if not description or not isinstance(description, string_types):
                    failed += 1
                    display_queue.append((echo_failure, '  required non-null string: description'))

                # groups
                groups = service_check.get('groups')
                if groups is None or not isinstance(groups, list):
                    failed += 1
                    display_queue.append((echo_failure, '  required list: groups'))

                # integration
                integration = service_check.get('integration')
                if integration is None or not isinstance(integration, string_types):
                    failed += 1
                    display_queue.append((echo_failure, '  required non-null string: integration'))

                # name
                name = service_check.get('name')
                if not name or not isinstance(name, string_types):
                    failed += 1
                    display_queue.append((echo_failure, '  required non-null string: name'))
                else:
                    if name in unique_names:
                        failed += 1
                        display_queue.append((echo_failure, '  {} is not a unique name'.format(name)))
                    else:
                        unique_names.add(name)

                # statuses
                statuses = service_check.get('statuses')
                if not statuses or not isinstance(statuses, list):
                    failed += 1
                    display_queue.append((echo_failure, '  required non empty list: statuses'))

            # See if anything happened
            if len(display_queue) > 1:
                for display, message in display_queue:
                    display(message)

    if failed > 0:
        abort()
