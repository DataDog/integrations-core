# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Agent probe captures: freeze, inventory-checks, check --json."""

from __future__ import annotations

import re
import subprocess


def _docker_exec(container: str, argv: list[str]) -> tuple[str, int]:
    res = subprocess.run(
        ['docker', 'exec', container, *argv],
        capture_output=True, text=True,
    )
    return res.stdout, res.returncode


def capture_freeze_probe(container_name: str, agent_cmd: str) -> tuple[str, int]:
    """Run ``agent integration freeze`` and return its stdout + rc.

    Output is normalised: lines starting with ``datadog-`` are sorted; any
    other line (warnings, etc.) is preserved at the end for triage.
    """

    out, rc = _docker_exec(container_name, [agent_cmd, 'integration', 'freeze'])
    datadog_lines = sorted(
        line for line in out.splitlines() if re.match(r'^datadog-[A-Za-z0-9_.\-]+==', line)
    )
    other_lines = [
        line for line in out.splitlines()
        if line and not re.match(r'^datadog-[A-Za-z0-9_.\-]+==', line)
    ]
    body = '\n'.join(datadog_lines)
    if other_lines:
        body += '\n# --- non-datadog output ---\n' + '\n'.join(other_lines)
    return body + '\n', rc


def capture_inventory_probe(container_name: str, agent_cmd: str) -> tuple[str, int]:
    """Run ``agent diagnose show-metadata inventory-checks`` and return stdout."""
    return _docker_exec(container_name, [agent_cmd, 'diagnose', 'show-metadata', 'inventory-checks'])


def capture_check_probe(
    *,
    container_name: str,
    agent_cmd: str,
    check_name: str,
    conf_path: str,
    readings: int,
    reading_interval: float,
    marker_path_in_container: str,
) -> tuple[str, int]:
    """Run ``agent check`` with the right reading mode and return JSON output.

    The shim's frozen clock advances based on a reading-index marker file.
    We reset that file to 0 before invoking the Agent so each compare run
    starts from a known offset.
    """

    # Reset reading-index marker.
    subprocess.run(
        ['docker', 'exec', container_name, 'sh', '-c', f'echo 0 > {marker_path_in_container}'],
        capture_output=True,
    )

    if readings == 1:
        time_flags: list[str] = []
    elif readings == 2 and abs(reading_interval - 1.0) < 1e-9:
        time_flags = ['--check-rate']
    else:
        time_flags = ['--check-times', str(readings), '--pause', str(int(reading_interval * 1000))]

    argv = [
        agent_cmd, 'check', check_name,
        '--json',
        '--delay', '1000',
        '-C', conf_path,
        *time_flags,
    ]
    return _docker_exec(container_name, argv)
