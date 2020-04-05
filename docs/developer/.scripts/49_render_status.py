import os

from datadog_checks.dev.tooling.constants import set_root
from datadog_checks.dev.tooling.utils import get_default_config_spec, get_valid_checks, get_valid_integrations

ROOT = os.getcwd()
set_root(ROOT)

MARKER = '<docs-insert-status>'


def patch(lines):
    """This renders the state of various aspects of integrations."""
    if not lines or not (lines[0] == '# Status' and MARKER in lines):
        return

    marker_index = lines.index(MARKER)
    new_lines = lines[:marker_index]

    for renderer in (
        render_config_spec_progress,
        render_dashboard_progress,
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
        dashboards_path = os.path.join(ROOT, integration, 'assets', 'dashboards')
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
