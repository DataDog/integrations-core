# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Top-N traffic reports: one custom report per dimension over the last 24 hours (opt-in).

Report jobs run one at a time. One still running after `REPORT_JOB_POLLS` polls is polled first by the next run,
never submitted again.
"""

from __future__ import annotations

import time
from typing import Literal
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall import constants
from datadog_checks.pan_firewall.constants import ACTIVE_STATUSES
from datadog_checks.pan_firewall.errors import PanosError, PanosUnreachable
from datadog_checks.pan_firewall.xml_utils import num, text

from .base import CollectContext, ReportJob, Sample

DEFAULT_TOP_N = 10
CAPTION = 'datadog'


def report_params(field: str, top_n: int) -> dict[str, str]:
    return {
        'type': 'report',
        'reporttype': 'dynamic',
        'reportname': 'custom-dynamic-report',
        'async': 'yes',
        'cmd': (
            f'<type><trsum><sortby>sessions</sortby><aggregate-by><member>{field}</member></aggregate-by>'
            '<values><member>sessions</member><member>bytes</member></values></trsum></type>'
            f'<period>last-24-hrs</period><topn>{top_n}</topn><topm>10</topm><caption>{CAPTION}</caption>'
        ),
    }


def parse_report(root: Element, name: str) -> list[Sample]:
    """A row missing its value or numbers is skipped. A country row can be a private range, kept as reported."""
    field, dimension = constants.REPORTS[name]
    samples: list[Sample] = []
    for entry in root.iterfind('result/report/entry'):
        value = text(entry, field)
        sessions, size = num(entry, 'sessions'), num(entry, 'bytes')
        if value is None or sessions is None or size is None:
            continue
        tags = (f'report:{name}', f'{dimension}:{value}')
        samples.append(Sample('report.top.sessions', sessions, tags, 'gauge'))
        samples.append(Sample('report.top.bytes', size, tags, 'gauge'))
        samples.append(Sample('report.top.bytes_per_session', size / sessions if sessions else 0, tags, 'gauge'))
    return samples


def collect_reports(ctx: CollectContext) -> list[Sample]:
    """Collect one cycle of `REPORTS`, resuming where the last run stopped. A job still running keeps `reports` due,
    so the next run, not the next interval, carries on with the cycle."""
    state = ctx.state.reports
    samples: list[Sample] = []

    if (job := state.pending) is not None:
        outcome, root = _poll(ctx, job)
        if outcome == 'running' and job.carries < constants.REPORT_MAX_CARRIES:
            job.carries += 1
            ctx.state.still_due.add('reports')
            return samples
        if outcome == 'running':
            ctx.warning(
                'the %s report job %s is still running after being carried over %d times: giving up on it',
                job.report,
                job.job_id,
                job.carries,
                once=False,
            )
        elif root is not None:
            samples += parse_report(root, job.report)
        state.pending = None

    top_n = ctx.config.report_top_n or DEFAULT_TOP_N
    reports = list(constants.REPORTS.items())
    while state.cursor < len(reports):
        name, (field, _dimension) = reports[state.cursor]
        job = ReportJob(name, ctx.client.submit_job(report_params(field, top_n)))
        state.cursor += 1
        state.pending = job
        outcome, root = _poll(ctx, job)
        if outcome == 'running':
            ctx.state.still_due.add('reports')
            return samples
        state.pending = None
        if root is not None:
            samples += parse_report(root, name)
    state.cursor = 0
    return samples


def _poll(ctx: CollectContext, job: ReportJob) -> tuple[Literal['finished', 'running', 'failed'], Element | None]:
    key, name = f'report:{job.report}', f'{job.report} report job {job.job_id}'
    for attempt in range(constants.REPORT_JOB_POLLS):
        try:
            status, root = ctx.client.get_job('report', job.job_id)
        except PanosUnreachable:
            raise
        except PanosError as e:
            ctx.warning('polling the %s failed: no samples for it (%s)', name, e, key=key)
            return 'failed', None
        if status == 'FIN':
            return 'finished', root
        if status not in ACTIVE_STATUSES:
            ctx.warning('the %s ended with status %s: no samples for it', name, status, key=key)
            return 'failed', None
        if attempt + 1 < constants.REPORT_JOB_POLLS:
            time.sleep(constants.REPORT_JOB_POLL_DELAY)
    return 'running', None
