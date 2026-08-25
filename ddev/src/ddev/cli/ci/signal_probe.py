# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Temporary probe: records which signals a ddev process receives when a workflow is cancelled.

GitHub documents SIGINT, then 7.5s, then SIGTERM, then 2.5s, then a hard kill of the process tree,
and also says a child of the step's entry process may get nothing before that kill. The Dispatcher's
cancellation handling depends on which of those actually reaches ddev, so this measures it rather
than assuming. Delete once the answer is recorded.
"""

from __future__ import annotations

import click

WATCHED_SIGNALS = ("SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT")


@click.command(short_help='Report which signals reach ddev, for cancellation testing', hidden=True)
@click.option('--duration', type=float, default=300.0, help='Seconds to stay alive.')
@click.option('--heartbeat', type=float, default=10.0, help='Seconds between heartbeat lines.')
def signal_probe(duration: float, heartbeat: float) -> None:
    """Stay alive, log every signal received, and keep going so a following signal is seen too.

    Deliberately does not exit on the first signal: the point is to observe the whole sequence, and
    exiting early would hide whether SIGTERM follows SIGINT.
    """
    import os
    import signal
    import sys
    import time

    start = time.monotonic()
    received: list[str] = []

    def report(line: str) -> None:
        print(f"[{time.monotonic() - start:7.2f}s] {line}", flush=True)

    def handler(signal_number: int, _frame: object) -> None:
        name = signal.Signals(signal_number).name
        received.append(name)
        report(f"RECEIVED {name}")

    for name in WATCHED_SIGNALS:
        number = getattr(signal, name, None)
        if number is not None:
            signal.signal(number, handler)

    report(f"pid={os.getpid()} ppid={os.getppid()} parent_cmd={_parent_command()}")
    report(f"watching {', '.join(WATCHED_SIGNALS)} for {duration}s")

    next_heartbeat = heartbeat
    while (elapsed := time.monotonic() - start) < duration:
        # Short sleeps so a handler runs promptly and the loop notices the deadline.
        time.sleep(0.2)
        if elapsed >= next_heartbeat:
            report(f"alive, signals so far: {received or 'none'}")
            next_heartbeat += heartbeat

    report(f"exiting normally, signals received: {received or 'none'}")
    sys.exit(0)


def _parent_command() -> str:
    """The parent's command line, to show whether ddev is the step's entry process or a child of it."""
    import os
    import subprocess

    try:
        return subprocess.run(
            ['ps', '-o', 'command=', '-p', str(os.getppid())],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception as error:  # noqa: BLE001 - a probe must not fail on its own diagnostics
        return f"unavailable ({error})"
