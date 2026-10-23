# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from collections import Counter
from types import SimpleNamespace
from unittest import mock
from xml.etree import ElementTree as ET

import pytest

from datadog_checks.pan_firewall import constants
from datadog_checks.pan_firewall.api import PanosClient
from datadog_checks.pan_firewall.auth import Credentials, KeyManager
from datadog_checks.pan_firewall.collectors.base import CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.threats import collect_threats
from datadog_checks.pan_firewall.errors import PanosApiError

from ..common import FIXTURES, FW_A_IP, FW_A_SERIAL, SYNTHETIC
from ..fixture_map import (
    BACKWARD_NEWEST_SEQNO,
    PROBE_SEQNO_FIRST_PAGE,
    PROBE_SEQNO_PAGE_SIZE,
    PROBE_SEQNO_PAGES,
    PROBE_SEQNO_START,
    THREAT_LOG_FIRST_SEQNO,
    seqno_query,
)
from ..helpers import THREAT_LOG_ACT as ACT
from ..helpers import THREAT_LOG_CLOCK_BACK as CLOCK_BACK
from ..helpers import FakeClock, log_page, make_instance, new_check, series

pytestmark = pytest.mark.unit

CACHE_KEY = f'threat_watermark:{FW_A_SERIAL}'
FW_A_LAST_SEQNO = 7691899338913481002
PROBE_LAST_SEQNO = 7691899338913582049
PROBE_ENTRIES = (PROBE_SEQNO_PAGES - 1) * PROBE_SEQNO_PAGE_SIZE + 5
EMPTY = (SYNTHETIC / 'threat_log_empty.xml').read_bytes()
NEWEST_AFTER_RESET = SYNTHETIC / 'threat_log_newest_after_reset.xml'
NO_CAPTURE = (200, b'<response status="error" code="400"><msg><line>no capture</line></msg></response>')
# What fw-a's `threat_log_5m.xml` holds: (severity, action, subtype, vsys) -> logs. 39 logs.
CAPTURE_COUNTS = {
    ('medium', 'drop', 'spyware', 'vsys1'): 22,
    ('critical', 'reset-both', 'vulnerability', 'vsys1'): 8,
    ('medium', 'reset-both', 'vulnerability', 'vsys1'): 8,
    ('medium', 'drop-packet', 'spyware', 'vsys1'): 1,
}
# The tags of a `log_page` entry, copied from a real log.
LOG_PAGE_TAGS = ('medium', 'drop', 'spyware', 'vsys1')


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_JOB_POLLS', 2)
    monkeypatch.setattr(constants, 'THREAT_JOB_POLL_DELAY', 0)


class Context:
    """A firewall's threats collector as the poller runs it: a real client on the fake transport, and a cache."""

    def __init__(self, fake_panos):
        self.fake = fake_panos
        self.cache = {}
        self.clock = FakeClock(100_000.0)
        http = new_check().http
        keys = KeyManager(http, FW_A_IP, Credentials(username=None, password=None, api_key='key'))
        log = mock.Mock()
        self.ctx = CollectContext(
            client=PanosClient(http, FW_A_IP, keys, log),
            identity=SimpleNamespace(serial=FW_A_SERIAL),
            state=FirewallState(),
            config=mock.Mock(),
            log=log,
            ip=FW_A_IP,
            clock=self.clock,
            read_cache=lambda key: self.cache.get(key, ''),
            write_cache=self.cache.__setitem__,
        )

    def collect(self):
        return collect_threats(self.ctx)

    def seed(self, seqno, last_reset_check=0.0):
        self.cache[CACHE_KEY] = json.dumps({'seqno': seqno, 'last_reset_check': last_reset_check})

    @property
    def watermark(self):
        raw = self.cache.get(CACHE_KEY)
        return json.loads(raw)['seqno'] if raw else None

    def answer_forward(self, watermark, *bodies, **seed):
        """Cache the watermark `watermark`, and answer the first page of the query from it with `bodies` in turn."""
        self.seed(watermark, **seed)
        self.fake.answer_log(FW_A_IP, 'forward', seqno_query(watermark + 1), *bodies)

    def submits(self):
        return [c.params for c in self.fake.calls_to(FW_A_IP) if c.type == 'log' and c.action is None]

    def backward_jobs(self):
        return [p for p in self.submits() if p['dir'] == 'backward']


@pytest.fixture
def firewall(fake_panos):
    return Context(fake_panos)


def tags(severity, action, subtype, vsys):
    return (f'severity:{severity}', f'action:{action}', f'subtype:{subtype}', f'vsys:{vsys}')


def expected(counts):
    return {('threat.count', tags(*key)): (n, 'count') for key, n in counts.items()}


def test_threat_logs_of_the_capture_are_counted_by_tag(firewall):
    firewall.seed(THREAT_LOG_FIRST_SEQNO['fw-a'] - 1)

    assert series(firewall.collect()) == expected(CAPTURE_COUNTS)


def test_first_run_reads_the_newest_log_and_counts_nothing(firewall):
    assert firewall.collect() == []

    assert firewall.submits() == [{'type': 'log', 'log-type': 'threat', 'dir': 'backward', 'nlogs': '1'}]
    assert firewall.watermark == BACKWARD_NEWEST_SEQNO


def test_first_run_on_a_firewall_without_threat_logs_tries_again_next_run(firewall):
    firewall.fake.answer_log(FW_A_IP, 'backward', None, EMPTY)

    firewall.collect()
    assert firewall.watermark is None
    firewall.fake.recover(FW_A_IP)
    firewall.collect()

    assert firewall.watermark == BACKWARD_NEWEST_SEQNO


def test_unreadable_cache_is_a_first_run(firewall):
    firewall.cache[CACHE_KEY] = 'not json'

    firewall.collect()

    assert firewall.watermark == BACKWARD_NEWEST_SEQNO


def answer_probe_pages(firewall, failing_page=None):
    """Answer the real `probe-seqno` pages, each from the newest `seqno` of the page before.

    Return the counts of their logs and the query each page is asked with.
    """
    counts = Counter()
    queries = []
    query = seqno_query(PROBE_SEQNO_START)
    for page in range(PROBE_SEQNO_FIRST_PAGE, PROBE_SEQNO_FIRST_PAGE + PROBE_SEQNO_PAGES):
        path = FIXTURES / 'probe-seqno' / f'seq_0_p{page}.xml'
        queries.append(query)
        firewall.fake.answer_log(FW_A_IP, 'forward', query, NO_CAPTURE if page == failing_page else path)
        entries = list(ET.parse(path).getroot().iterfind('result/log/logs/entry'))
        for entry in entries:
            counts[tuple(entry.findtext(f) for f in ('severity', 'action', 'subtype', 'vsys'))] += 1
        query = seqno_query(max(int(e.findtext('seqno')) for e in entries) + 1)
    return counts, queries


@pytest.fixture
def probe_pages(firewall, monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_PAGE_SIZE', PROBE_SEQNO_PAGE_SIZE)
    monkeypatch.setattr(constants, 'THREAT_MAX_PAGES', PROBE_SEQNO_PAGES)
    firewall.seed(PROBE_SEQNO_START - 1)


def test_seqno_paging_asks_each_page_from_the_newest_seqno_read(firewall, probe_pages):
    counts, queries = answer_probe_pages(firewall)

    samples = firewall.collect()

    assert [p['query'] for p in firewall.submits()] == queries
    assert series(samples) == expected(counts)
    assert firewall.watermark == PROBE_LAST_SEQNO


def test_failure_halfway_keeps_the_watermark_and_the_next_run_starts_over(firewall, probe_pages):
    answer_probe_pages(firewall, failing_page=PROBE_SEQNO_FIRST_PAGE + 2)

    with pytest.raises(PanosApiError):
        firewall.collect()

    assert firewall.watermark == PROBE_SEQNO_START - 1
    assert firewall.ctx.state.still_due == set()
    firewall.fake.recover(FW_A_IP)
    firewall.fake.calls.clear()
    answer_probe_pages(firewall)
    samples = firewall.collect()
    assert sum(s.value for s in samples) == PROBE_ENTRIES
    assert firewall.submits()[0]['query'] == seqno_query(PROBE_SEQNO_START)


def test_a_run_reads_at_most_the_page_cap_and_the_next_run_continues_from_there(firewall, monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_PAGE_SIZE', 2)
    assert constants.THREAT_MAX_PAGES == 2
    firewall.answer_forward(1000, log_page([1001, 1002]))
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1003), log_page([1003, 1004]))
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1005), log_page([1005]))

    first = firewall.collect()

    assert sum(s.value for s in first) == 4
    assert firewall.watermark == 1004
    assert firewall.ctx.state.still_due == {'threats'}
    assert len(firewall.submits()) == 2

    firewall.ctx.state.still_due.clear()
    second = firewall.collect()

    assert sum(s.value for s in second) == 1
    assert firewall.watermark == 1005
    assert [p['query'] for p in firewall.submits()][2] == seqno_query(1005)


def test_pages_counted_before_a_job_is_still_active_are_kept(firewall, monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_PAGE_SIZE', 2)
    firewall.answer_forward(1000, log_page([1001, 1002]))
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1003), ACT, ACT, log_page([1003]))

    assert firewall.collect() == []
    samples = firewall.collect()

    assert [p['query'] for p in firewall.submits()] == [seqno_query(1001), seqno_query(1003)]
    assert sum(s.value for s in samples) == 3
    assert firewall.watermark == 1003


def test_job_still_active_is_polled_next_run_without_resubmitting(firewall):
    firewall.answer_forward(1000, ACT, ACT, log_page([1001, 1002]))

    assert firewall.collect() == []
    assert firewall.watermark == 1000
    samples = firewall.collect()

    assert len(firewall.submits()) == 1
    assert sum(s.value for s in samples) == 2
    assert firewall.watermark == 1002


def test_failed_job_counts_nothing_and_the_next_run_submits_a_new_one(firewall):
    failed = ACT.replace(b'<status>ACT</status>', b'<status>FAIL</status>')
    firewall.answer_forward(1000, failed)

    with pytest.raises(PanosApiError, match='ended with status FAIL'):
        firewall.collect()

    assert firewall.watermark == 1000
    with pytest.raises(PanosApiError):
        firewall.collect()
    assert len(firewall.submits()) == 2


@pytest.mark.parametrize(
    'page, counts, watermark',
    [
        pytest.param(log_page([999, 1000, 1001, 1003]), {LOG_PAGE_TAGS: 2}, 1003, id='at-or-below-the-watermark'),
        pytest.param(log_page([1001, 'abc']), {LOG_PAGE_TAGS: 1}, 1001, id='invalid-seqno'),
        pytest.param(CLOCK_BACK, {LOG_PAGE_TAGS: 30}, 1030, id='clock-going-back'),
        pytest.param(log_page([1001], vsys='2'), {(*LOG_PAGE_TAGS[:3], 'vsys2'): 1}, 1001, id='vsys-n'),
    ],
)
def test_each_new_log_is_counted_once(firewall, page, counts, watermark):
    firewall.answer_forward(1000, page)

    samples = firewall.collect()

    assert series(samples) == expected(counts)
    assert firewall.watermark == watermark
    assert len(firewall.submits()) == 1


def test_a_missing_severity_action_subtype_or_vsys_leaves_the_tag_out(firewall):
    firewall.answer_forward(1000, log_page([1001], severity='', action='', subtype='', vsys=''))

    assert series(firewall.collect()) == {('threat.count', ()): (1, 'count')}


@pytest.mark.parametrize(
    'watermark, warnings',
    [
        # The newest seqno, 12, is below the watermark: seqno went backwards, the watermark is re-baselined.
        pytest.param(1000, 1, id='seqno-reset'),
        pytest.param(12, 0, id='newest-equal-to-the-watermark'),
    ],
)
def test_reset_check_rebaselines_with_a_warning_only_when_the_newest_seqno_is_below_the_watermark(
    firewall, watermark, warnings
):
    firewall.answer_forward(watermark, EMPTY)
    firewall.fake.answer_log(FW_A_IP, 'backward', None, NEWEST_AFTER_RESET)

    assert firewall.collect() == []

    assert json.loads(firewall.cache[CACHE_KEY]) == {'seqno': 12, 'last_reset_check': firewall.clock.now}
    assert firewall.ctx.log.warning.call_count == warnings


@pytest.mark.parametrize(
    'checked_ago, due',
    [
        pytest.param(30 * 60, True, id='30-minutes-ago'),
        pytest.param(29 * 60, False, id='29-minutes-ago'),
        # The time is monotonic, so after an Agent restart the persisted one can be ahead of the new clock.
        pytest.param(-10_000, True, id='ahead-of-the-clock'),
    ],
)
def test_reset_check_runs_every_30_minutes_when_nothing_new_is_counted(firewall, checked_ago, due):
    firewall.answer_forward(1000, EMPTY, last_reset_check=firewall.clock.now - checked_ago)

    firewall.collect()

    assert len(firewall.backward_jobs()) == int(due)


def test_a_pass_that_counted_logs_runs_no_reset_check(firewall):
    firewall.answer_forward(1000, log_page([1001]))

    firewall.collect()

    assert firewall.backward_jobs() == []


def test_threat_watermark_survives_a_restart_through_the_persistent_cache(dd_run_check, aggregator, fake_panos):
    # The first run has no watermark and starts one below fw-a's capture; a new check instance (an Agent restart)
    # then counts the capture from the persisted watermark, and persists the newest log it read.
    first = THREAT_LOG_FIRST_SEQNO['fw-a']
    fake_panos.answer_log(FW_A_IP, 'backward', None, log_page([first - 1]))
    dd_run_check(new_check())
    fake_panos.recover(FW_A_IP)

    check = new_check()
    dd_run_check(check)

    assert json.loads(check.read_persistent_cache(CACHE_KEY))['seqno'] == FW_A_LAST_SEQNO


def test_collect_threats_false_makes_no_log_call(dd_run_check, fake_panos):
    dd_run_check(new_check(make_instance(collect_threats=False)))

    assert [c for c in fake_panos.calls if c.type == 'log'] == []
