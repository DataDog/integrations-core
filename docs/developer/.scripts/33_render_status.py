import os

from datadog_checks.dev.tooling.utils import (
    get_available_logs_integrations,
    get_check_file,
    get_default_config_spec,
    get_valid_checks,
    get_valid_integrations,
    has_logs,
    has_agent_8_check_signature,
    has_dashboard,
    has_e2e,
    has_process_signature,
    has_saved_views,
    has_recommended_monitor,
    is_tile_only,
)

MARKER = '<docs-insert-status>'


def patch(lines):
    """This renders the status of various aspects of integrations."""
    if not lines or not (lines[0] == '# Status' and MARKER in lines):
        return

    marker_index = lines.index(MARKER)
    new_lines = lines[:marker_index]

    for renderer in (
        render_dashboard_progress,
        render_logs_progress,
        render_recommended_monitors_progress,
        render_config_spec_progress,
        render_e2e_progress,
        render_metadata_progress,
        render_process_signatures_progress,
        render_check_signatures_progress,
        render_saved_views_progress,
    ):
        new_lines.extend(renderer())
        new_lines.append('')

    # Remove unnecessary final newline
    new_lines.pop()

    new_lines.extend(lines[marker_index + 1:])
    return new_lines


def render_config_spec_progress():
    valid_checks = [x for x in sorted(get_valid_checks()) if not is_tile_only(x)]
    total_checks = len(valid_checks)
    checks_with_config_spec = 0

    lines = ['## Config specs', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        config_spec_path = get_default_config_spec(check)
        if os.path.isfile(config_spec_path):
            checks_with_config_spec += 1
            status = 'X'
        else:
            status = ' '

        lines.append(f'    - [{status}] {check}')

    percent = checks_with_config_spec / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    lines[4] = f'??? check "Completed {checks_with_config_spec}/{total_checks}"'
    return lines


def render_dashboard_progress():
    # Integrations that either do not emit metrics or have a too customer-specific setup to have an OOTBD
    not_possible = {
        'agent_metrics',  # Not for the end user
        'snmp',  # Too custom
        'openmetrics', # No default metrics
        'pdh_check',  # No default metrics
        'prometheus', # No default metrics
        'teamcity',  # No metrics
        'windows_service',  # No metrics
        'win32_event_log',  # No metrics
        'wmi_check',  # No default metrics
        'windows_service'  # No metrics
    }
    valid_integrations = sorted(set(get_valid_integrations()).difference(not_possible))
    total_integrations = len(valid_integrations)
    integrations_with_dashboard = 0

    lines = [
        '## Dashboards',
        '',
        '',
        '',
        '',
        None,
        '',
        '??? check "Completed"',
    ]

    for integration in valid_integrations:
        if has_dashboard(integration):
            integrations_with_dashboard += 1
            status = 'X'
        else:
            status = ' '

        lines.append(f'    - [{status}] {integration}')

    percent = integrations_with_dashboard / total_integrations * 100
    formatted_percent = f'{percent:.2f}'
    lines[5] = f'[={formatted_percent}% "{formatted_percent}%"]'
    lines[7] = f'??? check "Completed {integrations_with_dashboard}/{total_integrations}"'
    return lines


def render_metadata_progress():
    valid_checks = [x for x in sorted(get_valid_checks()) if not is_tile_only(x)]
    total_checks = len(valid_checks)
    checks_with_metadata = 0

    lines = ['## Metadata submission', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        status = ' '
        check_file = get_check_file(check)
        if os.path.exists(check_file):
            with open(check_file, 'r', encoding='utf-8') as f:
                contents = f.read()
                if 'self.set_metadata' in contents:
                    status = 'X'
                    checks_with_metadata += 1
        lines.append(f'    - [{status}] {check}')

    percent = checks_with_metadata / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    lines[4] = f'??? check "Completed {checks_with_metadata}/{total_checks}"'
    return lines


def render_logs_progress():
    valid_checks = get_available_logs_integrations()
    total_checks = len(valid_checks)
    checks_with_logs = 0

    lines = ['## Logs support', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        status = None
        tile_only = is_tile_only(check)
        check_has_logs = has_logs(check)

        if not tile_only:
            status = ' '
        if check_has_logs:
            status = 'X'
            checks_with_logs += 1

        if status != 'X' and tile_only:
            total_checks -= 1  # we cannot really add log collection to tile only integrations

        if status is not None:
            lines.append(f'    - [{status}] {check}')

    percent = checks_with_logs / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    lines[4] = f'??? check "Completed {checks_with_logs}/{total_checks}"'
    return lines


def render_e2e_progress():
    valid_checks = [x for x in sorted(get_valid_checks()) if not is_tile_only(x)]
    total_checks = len(valid_checks)
    checks_with_e2e = 0

    lines = ['## E2E tests', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        if has_e2e(check):
            status = 'X'
            checks_with_e2e += 1
        else:
            status = ' '
        lines.append(f'    - [{status}] {check}')

    percent = checks_with_e2e / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    lines[4] = f'??? check "Completed {checks_with_e2e}/{total_checks}"'
    return lines


def render_process_signatures_progress():
    exclude = {'datadog_checks_base', 'datadog_checks_dev', 'datadog_checks_downloader', 'snowflake'}
    valid_checks = sorted([c for c in get_valid_checks() if c not in exclude])
    total_checks = len(valid_checks)
    checks_with_ps = 0

    lines = ['## Process signatures', '', None, '', '??? check "Completed"']
    for check in valid_checks:
        if has_process_signature(check):
            status = 'X'
            checks_with_ps += 1
        else:
            status = ' '
        lines.append(f'    - [{status}] {check}')

    percent = checks_with_ps / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    lines[4] = f'??? check "Completed {checks_with_ps}/{total_checks}"'
    return lines


def render_check_signatures_progress():
    exclude = {'datadog_checks_base', 'datadog_checks_dev', 'datadog_checks_downloader'}
    valid_checks = sorted([c for c in get_valid_checks() if c not in exclude])
    total_checks = len(valid_checks)
    checks_with_cs = 0

    lines = ['## Agent 8 check signatures', '', None, '', '??? check "Completed"']
    for check in valid_checks:
        if has_agent_8_check_signature(check):
            status = 'X'
            checks_with_cs += 1
        else:
            status = ' '
        lines.append(f'    - [{status}] {check}')

    percent = checks_with_cs / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    lines[4] = f'??? check "Completed {checks_with_cs}/{total_checks}"'
    return lines


def render_saved_views_progress():
    valid_checks = [x for x in sorted(get_valid_checks()) if not is_tile_only(x)]
    total_checks = len(valid_checks)
    checks_with_sv = 0

    lines = ['## Default saved views', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        if has_saved_views(check):
            checks_with_sv += 1
            status = 'X'
        else:
            status = ' '

        lines.append(f'    - [{status}] {check}')

    percent = checks_with_sv / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    lines[4] = f'??? check "Completed {checks_with_sv}/{total_checks}"'
    return lines


def render_recommended_monitors_progress():
    valid_checks = [x for x in sorted(get_valid_checks()) if not is_tile_only(x)]
    total_checks = len(valid_checks)
    checks_with_rm = 0

    lines = ['## Recommended monitors', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        if has_recommended_monitor(check):
            checks_with_rm += 1
            status = 'X'
        else:
            status = ' '

        lines.append(f'    - [{status}] {check}')

    percent = checks_with_rm / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    lines[4] = f'??? check "Completed {checks_with_rm}/{total_checks}"'
    return lines
