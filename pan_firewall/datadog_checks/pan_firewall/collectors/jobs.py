# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The commit check: is a commit or content update running or queued on the firewall?

It is not a scheduled collector and submits nothing: the poller calls `busy_jobs()` before any collector runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall.constants import ACTIVE_STATUSES, BUSY_JOB_TYPES
from datadog_checks.pan_firewall.xml_utils import text

if TYPE_CHECKING:
    from datadog_checks.pan_firewall.api import PanosClient

# Not `show jobs all`, which returns the whole job history (380 KB after one week in the lab).
JOBS_PENDING_CMD = '<show><jobs><pending/></jobs></show>'


class BusyJob(NamedTuple):
    type: str
    id: str


def parse_busy_jobs(root: Element) -> list[BusyJob]:
    busy = []
    # Every `<job>` element, wherever it sits: the `show jobs pending` envelope is not verified on a real device yet.
    for job in root.iter('job'):
        job_type = text(job, 'type')
        if job_type in BUSY_JOB_TYPES and text(job, 'status') in ACTIVE_STATUSES:
            busy.append(BusyJob(job_type, text(job, 'id') or 'unknown'))
    return busy


def busy_jobs(client: PanosClient) -> list[BusyJob]:
    return parse_busy_jobs(client.op(JOBS_PENDING_CMD))
