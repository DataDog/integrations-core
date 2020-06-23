import os

from datadog_checks.dev.tooling.utils import (
    get_check_file,
    get_config_file,
    get_default_config_spec,
    get_readme_file,
    get_valid_checks,
    get_valid_integrations,
    is_tile_only, has_e2e, has_dashboard)
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
        if has_dashboard(integration):
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
    return lines


def render_logs_progress():
    valid_checks = sorted(get_valid_checks())
    total_checks = len(valid_checks)
    checks_with_logs = 0

    lines = ['## Logs support', '', None, '', '??? check "Completed"']

    for check in valid_checks:
        status = None

        if not is_tile_only(check):
            status = ' '
            config_file = get_config_file(check)

            with open(config_file, 'r', encoding='utf-8') as f:
                if '# logs:' in f.read():
                    status = 'X'
                    checks_with_logs += 1
        else:
            readme_file = get_readme_file(check)
            if os.path.exists(readme_file):
                with open(readme_file, 'r', encoding='utf-8') as f:
                    if '# Log collection' in f.read():
                        status = 'X'
                        checks_with_logs += 1
            if status != 'X':
                total_checks -= 1  # we cannot really add log collection to tile only integrations

        if status is not None:
            lines.append(f'    - [{status}] {check}')

    percent = checks_with_logs / total_checks * 100
    formatted_percent = f'{percent:.2f}'
    lines[2] = f'[={formatted_percent}% "{formatted_percent}%"]'
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
    return lines
