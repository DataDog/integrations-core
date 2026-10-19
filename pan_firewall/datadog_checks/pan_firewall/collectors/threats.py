# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Threat log counts (`threat.count`).

Logs are read by `seqno`, never by time: the query asks for every log from `watermark + 1` on, oldest first, paged
with `skip`. The watermark is the `seqno` of the last log counted; it is persisted by firewall serial and only moves
after a pass that read every page, so a failure halfway leaves it, and the counts, where they were.
"""

from __future__ import annotations

import time
from xml.etree.ElementTree import Element

from datadog_checks.pan_firewall import constants
from datadog_checks.pan_firewall.constants import ACTIVE_STATUSES, PARSE_ERROR_CODE
from datadog_checks.pan_firewall.errors import PanosApiError
from datadog_checks.pan_firewall.identity import normalize_vsys
from datadog_checks.pan_firewall.xml_utils import text

from .base import CollectContext, Sample, ThreatJob, ThreatState, Watermark, register, tag_tuple


@register('threats')
def collect_threats(ctx: CollectContext) -> list[Sample]:
    """Run one pass, from the job left running or the watermark. Samples come only from a complete pass."""
    state = ctx.state.threats
    _load_watermark(ctx, state)
    job: ThreatJob | None = state.pending or _first_job(state)
    state.pending = None
    while job is not None:
        if not _fetch(ctx, job):
            state.pending = job
            ctx.state.still_due.add('threats')
            ctx.debug('threat log job %s still running, polled again next run', job.job_id)
            return []
        if job.purpose == 'forward' and job.page_entries >= job.page_size:
            job.skip += job.page_size
            job.job_id = None
            job.page_entries = 0
            continue
        samples, job = _complete(ctx, state, job)
        if job is None:
            return samples
    return []


def _load_watermark(ctx: CollectContext, state: ThreatState) -> None:
    if state.loaded:
        return
    state.loaded = True
    serial = ctx.identity.serial
    raw = serial and ctx.read_cache(_cache_key(serial))
    if not raw:
        return
    try:
        state.watermark = Watermark.from_json(raw)
    except (ValueError, TypeError, KeyError) as e:
        ctx.debug('ignoring the cached threat watermark: %s', e)


def _cache_key(serial: str) -> str:
    return f'threat_watermark:{serial}'


def _store(ctx: CollectContext, state: ThreatState, seqno: int, last_reset_check: float) -> None:
    watermark = state.watermark = Watermark(seqno, last_reset_check)
    if serial := ctx.identity.serial:
        ctx.write_cache(_cache_key(serial), watermark.to_json())


def _first_job(state: ThreatState) -> ThreatJob:
    if state.watermark is None:
        return ThreatJob('baseline')
    return ThreatJob('forward', base_seqno=state.watermark.seqno, page_size=constants.THREAT_PAGE_SIZE)


def _params(job: ThreatJob) -> dict[str, str]:
    params = {'type': 'log', 'log-type': 'threat'}
    if job.purpose == 'forward':
        return {
            **params,
            'dir': 'forward',
            'nlogs': str(job.page_size),
            'skip': str(job.skip),
            'query': f'(seqno geq {job.base_seqno + 1})',
        }
    return {**params, 'dir': 'backward', 'nlogs': '1'}


def _fetch(ctx: CollectContext, job: ThreatJob) -> bool:
    """Return False if the job is still running."""
    client = ctx.client
    if job.job_id is None:
        job.job_id = client.submit_job(_params(job))
    for attempt in range(constants.THREAT_JOB_POLLS):
        status = client.read_log_job(job.job_id, lambda entry: _add(ctx, job, entry))
        if status == 'FIN':
            return True
        if status not in ACTIVE_STATUSES:
            raise PanosApiError(PARSE_ERROR_CODE, f'threat log job {job.job_id} ended with status {status}')
        if attempt + 1 < constants.THREAT_JOB_POLLS:
            time.sleep(constants.THREAT_JOB_POLL_DELAY)
    return False


def _add(ctx: CollectContext, job: ThreatJob, entry: Element) -> None:
    job.page_entries += 1
    try:
        seqno = int(entry.findtext('seqno') or '')
    except ValueError:
        ctx.debug('skipping a threat log entry with a missing or invalid seqno %r', entry.findtext('seqno'))
        return
    # A log at or below the watermark should not come back from the query; drop it if it does.
    if job.purpose == 'forward' and seqno <= job.base_seqno:
        return
    if job.newest_seqno is None or seqno > job.newest_seqno:
        job.newest_seqno = seqno
    if job.purpose == 'forward':
        job.counted += 1
        key = (
            text(entry, 'severity') or '',
            text(entry, 'action') or '',
            text(entry, 'subtype') or '',
            normalize_vsys(text(entry, 'vsys')) or '',
        )
        job.counts[key] += 1


def _complete(ctx: CollectContext, state: ThreatState, job: ThreatJob) -> tuple[list[Sample], ThreatJob | None]:
    now = ctx.clock()
    watermark = state.watermark
    if job.purpose == 'baseline':
        # No log yet: the watermark stays unset and the next run tries again.
        if job.newest_seqno is not None:
            _store(ctx, state, job.newest_seqno, now)
        return [], None
    assert watermark is not None
    if job.purpose == 'forward':
        if job.counted:
            assert job.newest_seqno is not None
            _store(ctx, state, job.newest_seqno, watermark.last_reset_check)
            return _samples(job), None
        due = (
            watermark.last_reset_check > now or now - watermark.last_reset_check >= constants.THREAT_RESET_CHECK_SECONDS
        )
        return [], ThreatJob('reset') if due else None
    # `reset`: a newest log below the watermark means `seqno` went backwards.
    if job.newest_seqno is not None and job.newest_seqno < watermark.seqno:
        ctx.warning(
            'the newest threat log has seqno %d, below the last counted one (%d): the firewall '
            'restarted or failed over. Counting restarts from there; logs written since are not counted.',
            job.newest_seqno,
            watermark.seqno,
            once=False,
        )
        _store(ctx, state, job.newest_seqno, now)
    else:
        _store(ctx, state, watermark.seqno, now)
    return [], None


def _samples(job: ThreatJob) -> list[Sample]:
    return [
        Sample(
            'threat.count',
            count,
            tag_tuple(('severity', severity), ('action', action), ('subtype', subtype), ('vsys', vsys)),
            'count',
        )
        for (severity, action, subtype, vsys), count in sorted(job.counts.items())
    ]
