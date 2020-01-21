# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import click

from ....utils import file_exists, read_file
from ...constants import get_root
from ...utils import get_valid_integrations, load_manifest, parse_version_parts
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

REQUIRED_ATTRIBUTES = {'agent_version', 'check', 'description', 'groups', 'integration', 'name', 'statuses'}


@click.command('service-checks', context_settings=CONTEXT_SETTINGS, short_help='Validate `service_checks.json` files')
def service_checks():
    """Validate all `service_checks.json` files."""
    root = get_root()
    echo_info("Validating all service_checks.json files...")
    failed_checks = 0
    ok_checks = 0

    for check_name in sorted(get_valid_integrations()):
        display_queue = []
        file_failed = False
        manifest = load_manifest(check_name)
        service_check_relative = manifest.get('assets', {}).get('service_checks', '')
        service_checks_file = os.path.join(root, check_name, *service_check_relative.split('/'))

        if not file_exists(service_checks_file):
            echo_info(f'{check_name}/service_checks.json... ', nl=False)
            echo_failure('FAILED')
            echo_failure('  service_checks.json file does not exist')
            failed_checks += 1
            continue

        try:
            decoded = json.loads(read_file(service_checks_file).strip())
        except json.JSONDecodeError as e:
            failed_checks += 1
            echo_info(f'{check_name}/service_checks.json... ', nl=False)
            echo_failure('FAILED')
            echo_failure(f'  invalid json: {e}')
            continue

        unique_names = set()
        unique_checks = set()
        for service_check in decoded:
            # attributes are valid
            attrs = set(service_check)
            for attr in sorted(attrs - REQUIRED_ATTRIBUTES):
                file_failed = True
                display_queue.append((echo_failure, f'  Attribute `{attr}` is invalid'))
            for attr in sorted(REQUIRED_ATTRIBUTES - attrs):
                file_failed = True
                display_queue.append((echo_failure, f'  Attribute `{attr}` is required'))

            # agent_version
            agent_version = service_check.get('agent_version')
            version_parts = parse_version_parts(agent_version)
            if len(version_parts) != 3:
                file_failed = True

                if not agent_version:
                    output = '  required non-null string: agent_version'
                else:
                    output = f'  invalid `agent_version`: {agent_version}'

                display_queue.append((echo_failure, output))

            # check
            check = service_check.get('check')
            if not check or not isinstance(check, str):
                file_failed = True
                display_queue.append((echo_failure, '  required non-null string: check'))
            else:
                if check in unique_checks:
                    file_failed = True
                    display_queue.append((echo_failure, f'  {check} is not a unique check'))
                else:
                    unique_checks.add(check)

            # description
            description = service_check.get('description')
            if not description or not isinstance(description, str):
                file_failed = True
                display_queue.append((echo_failure, '  required non-null string: description'))

            # groups
            groups = service_check.get('groups')
            if groups is None or not isinstance(groups, list):
                file_failed = True
                display_queue.append((echo_failure, '  required list: groups'))

            # integration
            integration = service_check.get('integration')
            if integration is None or not isinstance(integration, str):
                file_failed = True
                display_queue.append((echo_failure, '  required non-null string: integration'))

            # name
            name = service_check.get('name')
            if not name or not isinstance(name, str):
                file_failed = True
                display_queue.append((echo_failure, '  required non-null string: name'))
            else:
                if name in unique_names:
                    file_failed = True
                    display_queue.append((echo_failure, f'  {name} is not a unique name'))
                else:
                    unique_names.add(name)

            # statuses
            statuses = service_check.get('statuses')
            if not statuses or not isinstance(statuses, list):
                file_failed = True
                display_queue.append((echo_failure, '  required non empty list: statuses'))

        if file_failed:
            failed_checks += 1
            # Display detailed info if file invalid
            echo_info(f"{check_name}/service_checks.json... ", nl=False)
            echo_failure("FAILED")
            for display_func, message in display_queue:
                display_func(message)
        else:
            ok_checks += 1

    if ok_checks:
        echo_success(f"{ok_checks} valid files")
    if failed_checks:
        echo_failure(f"{failed_checks} invalid files")
        abort()
