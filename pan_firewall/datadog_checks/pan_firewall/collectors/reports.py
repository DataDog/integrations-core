# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Top-N traffic reports: one custom dynamic report per dimension over the last 24 hours (`reports`, opt-in).

The firewall builds a report as an asynchronous job. The jobs run one at a time, each polled to its end before the
next is submitted. A job still running after `REPORT_JOB_POLLS` polls is kept in `FirewallState.reports` and polled
first by the next run, never submitted again.
"""

from __future__ import annotations

import time
from typing import Literal
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall import constants
from datadog_checks.pan_firewall.xml_utils import num, text

from . import CollectContext, ReportJob, Sample, register, warn_once

DEFAULT_TOP_N = 10
ACTIVE_STATUSES = frozenset({'ACT', 'PEND'})
CAPTION = 'datadog'


def report_params(field: str, top_n: int) -> dict[str, str]:
    """Return the request submitting a report of the `top_n` values of `field` by sessions, with their bytes."""
    return {
        'type': 'report',
        'reporttype': 'dynamic',
        'reportname': 'custom-dynamic-report',
        'cmd': (
            f'<type><trsum><sortby>sessions</sortby><aggregate-by><member>{field}</member></aggregate-by>'
            '<values><member>sessions</member><member>bytes</member></values></trsum></type>'
            f'<period>last-24-hrs</period><topn>{top_n}</topn><topm>10</topm><caption>{CAPTION}</caption>'
        ),
    }


def parse_report(root: Element, name: str) -> list[Sample]:
    """Return sessions, bytes and bytes per session of each row; a row missing its value or numbers is skipped.

    A country row can be a private range (`10.0.0.0-10.255.255.255`): it is kept as the firewall reports it.
    """
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


@register('reports')
def collect_reports(ctx: CollectContext) -> list[Sample]:
    state = ctx.state.reports
    samples: list[Sample] = []
    done: set[str] = set()  # reports that need no new job this run

    pending, state.pending = state.pending, None
    if pending is not None:
        done.add(pending.report)
        outcome, root = _poll(ctx, pending)
        if outcome == 'running':
            if pending.carries < constants.REPORT_MAX_CARRIES:
                pending.carries += 1
                state.pending = pending
                return samples
            # Dropped, and not submitted again before the next run, so the reports after it are not held back.
            ctx.log.warning(
                'pan_firewall: the %s report job %s is still running after %d runs: giving up on it',
                pending.report,
                pending.job_id,
                pending.carries,
            )
        elif root is not None:
            samples += parse_report(root, pending.report)

    top_n = ctx.config.report_top_n or DEFAULT_TOP_N
    for name, (field, _dimension) in constants.REPORTS.items():
        if name in done:
            continue
        job = ReportJob(name, ctx.client.submit_job(report_params(field, top_n)))
        outcome, root = _poll(ctx, job)
        if outcome == 'running':
            state.pending = job
            break
        if root is not None:
            samples += parse_report(root, name)
    return samples


def _poll(ctx: CollectContext, job: ReportJob) -> tuple[Literal['finished', 'running', 'failed'], Element | None]:
    """Poll the job until it ends: `finished` with its response, `failed` (warned once) or still `running`."""
    for attempt in range(constants.REPORT_JOB_POLLS):
        status, root = ctx.client.get_job('report', job.job_id)
        if status == 'FIN':
            return 'finished', root
        if status not in ACTIVE_STATUSES:
            warn_once(
                ctx,
                f'report:{job.report}',
                'pan_firewall: the %s report job %s ended with status %s: no samples for it',
                job.report,
                job.job_id,
                status,
            )
            return 'failed', None
        if attempt + 1 < constants.REPORT_JOB_POLLS:
            time.sleep(constants.REPORT_JOB_POLL_DELAY)
    return 'running', None
