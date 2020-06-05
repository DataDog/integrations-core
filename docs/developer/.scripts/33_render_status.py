import os

from datadog_checks.dev.tooling.constants import get_root
from datadog_checks.dev.tooling.utils import get_default_config_spec, get_valid_checks, get_valid_integrations, \
    get_config_file, get_check_file

MARKER = '<docs-insert-status>'


def patch(lines):
    """This renders the status of various aspects of integrations."""
    if not lines or not (lines[0] == '# Status' and MARKER in lines):
        return

    marker_index = lines.index(MARKER)
    new_lines = lines[:marker_index]

    for renderer in (
        render_config_spec_progress,
        render_dashboard_progress,
        render_metadata_progress,
        render_logs_progress,
        render_e2e_progress
    ):
        new_lines.extend(renderer())
        new_lines.append('')

    # Remove unnecessary final newline
    new_lines.pop()

    new_lines.extend(lines[marker_index + 1:])
    return new_lines


def render_config_spec_progress():
    valid_checks = sorted(get_valid_checks())
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
    return lines


def render_dashboard_progress():
    valid_integrations = sorted(get_valid_integrations())
    total_integrations = len(valid_integrations)
    integrations_with_dashboard = 0

    lines = [
        '## Dashboards',
        '',
        '!!! note',
        '    This is not representative of _all_ dashboards, as many exist in legacy locations.',
        '',
        None,
        '',
        '??? check "Completed"',
    ]

    for integration in valid_integrations:
        dashboards_path = os.path.join(get_root(), integration, 'assets', 'dashboards')
        if os.path.isdir(dashboards_path) and len(os.listdir(dashboards_path)) > 0:
            integrations_with_dashboard += 1
            status = 'X'
        else:
            status = ' '

        lines.append(f'    - [{status}] {integration}')

    percent = integrations_with_dashboard / total_integrations * 100
    formatted_percent = f'{percent:.2f}'
    lines[5] = f'[={formatted_percent}% "{formatted_percent}%"]'
    return lines


def render_metadata_progress():
    valid_checks = sorted(get_valid_checks())
    total_checks = len(valid_checks)
    checks_with_metadata = 0

    lines = ['## Metadata', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        config_file = get_config_file(check)
        status = ' '
        if not os.path.exists(config_file):
            # tile only
            total_checks -= 1
        else:
            check_file = get_check_file(check)
            if os.path.exists(check_file):
                with open(check_file) as f:
                    contents = f.read()
                    if 'self.set_metadata' in contents:
                        status = 'X'
                        checks_with_metadata += 1

        lines.append(f'    - [{status}] {check}')

    percent = checks_with_metadata / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    return lines


def render_logs_progress():
    valid_checks = sorted(get_valid_checks())
    total_checks = len(valid_checks)
    checks_with_logs = 0

    lines = ['## Logs specs', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        config_file = get_config_file(check)
        status = ' '
        if os.path.exists(config_file):
            with open(config_file) as f:
                if '# logs:' in f.read():
                    status = 'X'
                    checks_with_logs += 1

        lines.append(f'    - [{status}] {check}')

    percent = checks_with_logs / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    return lines


def render_e2e_progress():
    valid_checks = sorted(get_valid_checks())
    total_checks = len(valid_checks)
    checks_with_e2e = 0

    lines = ['## E2E', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        config_file = get_config_file(check)
        status = ' '
        if not os.path.exists(config_file):
            # tile only
            total_checks -= 1
        else:
            with open(config_file) as f:
                if '# logs:' in f.read():
                    status = 'X'
                    checks_with_e2e += 1

        lines.append(f'    - [{status}] {check}')

    percent = checks_with_e2e / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
    return lines
