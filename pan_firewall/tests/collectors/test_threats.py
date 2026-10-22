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


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_JOB_POLLS', 2)
    monkeypatch.setattr(constants, 'THREAT_JOB_POLL_DELAY', 0)


class Context:
    """A firewall's threats collector as the poller runs it: a real client on the fake transport, and a cache."""

    def __init__(self, fake_panos, cache=None, clock=None, host=FW_A_IP):
        self.fake = fake_panos
        self.cache = {} if cache is None else cache
        self.clock = clock or FakeClock(100_000.0)
        self.host = host
        self.log = mock.Mock()
        self.restart()

    def restart(self):
        """New in-memory state over the same cache, as after an Agent restart."""
        log = self.log
        http = new_check().http
        keys = KeyManager(http, self.host, Credentials(username=None, password=None, api_key='key'))
        self.ctx = CollectContext(
            client=PanosClient(http, self.host, keys, log),
            identity=SimpleNamespace(serial=FW_A_SERIAL),
            state=FirewallState(),
            config=mock.Mock(),
            log=log,
            ip=self.host,
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
        self.fake.answer_log(self.host, 'forward', seqno_query(watermark + 1), 0, *bodies)

    def submits(self):
        return [c.params for c in self.fake.calls_to(self.host) if c.type == 'log' and c.action is None]

    def backward_jobs(self):
        return [p for p in self.submits() if p['dir'] == 'backward']


@pytest.fixture
def firewall(fake_panos):
    return Context(fake_panos)


def tags(severity, action, subtype, vsys):
    return (f'severity:{severity}', f'action:{action}', f'subtype:{subtype}', f'vsys:{vsys}')


def expected(counts):
    return {('threat.count', tags(*key)): (n, 'count') for key, n in counts.items()}


def probe_counts():
    """Tag counts and seqnos of the `probe-seqno` pages, read from the fixtures."""
    counts, seqnos = Counter(), []
    for page in range(PROBE_SEQNO_FIRST_PAGE, PROBE_SEQNO_FIRST_PAGE + PROBE_SEQNO_PAGES):
        root = ET.parse(FIXTURES / 'probe-seqno' / f'seq_0_p{page}.xml').getroot()
        for entry in root.iterfind('result/log/logs/entry'):
            counts[tuple(entry.findtext(f) for f in ('severity', 'action', 'subtype', 'vsys'))] += 1
            seqnos.append(int(entry.findtext('seqno')))
    return counts, seqnos


def test_threat_logs_of_the_capture_are_counted_by_tag(firewall):
    firewall.seed(THREAT_LOG_FIRST_SEQNO['fw-a'] - 1)

    samples = firewall.collect()

    assert series(samples) == expected(CAPTURE_COUNTS)


def test_first_run_reads_the_newest_log_and_counts_nothing(firewall):
    samples = firewall.collect()

    assert samples == []
    (params,) = firewall.submits()
    assert params == {'type': 'log', 'log-type': 'threat', 'dir': 'backward', 'nlogs': '1'}
    assert firewall.watermark == BACKWARD_NEWEST_SEQNO


def test_first_run_on_a_firewall_without_threat_logs_tries_again_next_run(firewall):
    firewall.fake.answer_log(FW_A_IP, 'backward', None, 0, EMPTY)

    assert firewall.collect() == []
    assert firewall.watermark is None
    firewall.fake.recover(FW_A_IP)
    assert firewall.collect() == []

    assert [p['dir'] for p in firewall.submits()] == ['backward', 'backward']
    assert firewall.watermark == BACKWARD_NEWEST_SEQNO


def test_seqno_paging_fetches_every_page_in_order_without_duplicates(firewall, monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_PAGE_SIZE', PROBE_SEQNO_PAGE_SIZE)
    firewall.seed(PROBE_SEQNO_START - 1)
    counts, seqnos = probe_counts()

    samples = firewall.collect()

    assert [(p['skip'], p['nlogs'], p['query']) for p in firewall.submits()] == [
        (str(page * PROBE_SEQNO_PAGE_SIZE), '20', seqno_query(PROBE_SEQNO_START)) for page in range(PROBE_SEQNO_PAGES)
    ]
    assert series(samples) == expected(counts)
    assert firewall.watermark == PROBE_LAST_SEQNO == max(seqnos)
    # Each finished page is read with one request.
    gets = [c for c in firewall.fake.calls if c.type == 'log' and c.action == 'get']
    assert len(gets) == len(firewall.submits()) == PROBE_SEQNO_PAGES


def test_same_window_again_counts_nothing(firewall, monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_PAGE_SIZE', PROBE_SEQNO_PAGE_SIZE)
    firewall.seed(PROBE_SEQNO_START - 1, last_reset_check=firewall.clock.now)
    firewall.collect()
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(PROBE_LAST_SEQNO + 1), 0, EMPTY)
    submits_before = len(firewall.submits())

    assert firewall.collect() == []

    assert firewall.submits()[submits_before:] == [
        {
            'type': 'log',
            'log-type': 'threat',
            'dir': 'forward',
            'nlogs': '20',
            'skip': '0',
            'query': seqno_query(PROBE_LAST_SEQNO + 1),
        }
    ]
    assert firewall.watermark == PROBE_LAST_SEQNO


def test_logs_at_or_below_the_watermark_are_dropped(firewall):
    firewall.answer_forward(1000, log_page([999, 1000, 1001, 1003]))

    samples = firewall.collect()

    assert series(samples) == expected({('medium', 'drop', 'spyware', 'vsys1'): 2})
    assert firewall.watermark == 1003


def test_a_full_page_of_5000_asks_for_the_next_one(firewall):
    first = log_page(range(1001, 6001))
    firewall.answer_forward(1000, first)
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 5000, log_page(range(6001, 6004)))

    samples = firewall.collect()

    assert [p['skip'] for p in firewall.submits()] == ['0', '5000']
    assert sum(s.value for s in samples) == 5003
    assert firewall.watermark == 6003


def test_restart_resumes_from_the_persisted_watermark(firewall):
    firewall.seed(THREAT_LOG_FIRST_SEQNO['fw-a'] - 1)
    firewall.collect()
    assert firewall.watermark == FW_A_LAST_SEQNO
    firewall.restart()
    firewall.fake.calls.clear()
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(FW_A_LAST_SEQNO + 1), 0, EMPTY)

    assert firewall.collect() == []

    assert firewall.submits()[0]['query'] == seqno_query(FW_A_LAST_SEQNO + 1)


def test_unreadable_cache_is_a_first_run(firewall):
    firewall.cache[CACHE_KEY] = 'not json'

    assert firewall.collect() == []

    assert [p['dir'] for p in firewall.submits()] == ['backward']
    assert firewall.watermark == BACKWARD_NEWEST_SEQNO


def test_failure_halfway_keeps_the_watermark_and_the_next_run_starts_over(firewall, monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_PAGE_SIZE', PROBE_SEQNO_PAGE_SIZE)
    firewall.seed(PROBE_SEQNO_START - 1)
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(PROBE_SEQNO_START), 40, NO_CAPTURE)

    with pytest.raises(PanosApiError):
        firewall.collect()

    assert firewall.watermark == PROBE_SEQNO_START - 1
    firewall.fake.recover(FW_A_IP)
    firewall.fake.calls.clear()
    samples = firewall.collect()
    assert sum(s.value for s in samples) == PROBE_ENTRIES
    assert firewall.submits()[0]['skip'] == '0'
    assert firewall.watermark == PROBE_LAST_SEQNO


def test_clock_going_back_counts_every_log_once_with_no_extra_job(firewall):
    firewall.answer_forward(1000, CLOCK_BACK)

    samples = firewall.collect()

    assert series(samples) == expected({('medium', 'drop', 'spyware', 'vsys1'): 30})
    assert firewall.watermark == 1030
    assert len(firewall.submits()) == 1


def nothing_new(firewall, watermark=1000, last_reset_check=0.0, newest=None):
    firewall.answer_forward(watermark, EMPTY, last_reset_check=last_reset_check)
    if newest is not None:
        firewall.fake.answer_log(FW_A_IP, 'backward', None, 0, newest)


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
    nothing_new(firewall, watermark=watermark, newest=NEWEST_AFTER_RESET)

    assert firewall.collect() == []

    assert firewall.watermark == 12
    assert len(firewall.backward_jobs()) == 1
    assert firewall.ctx.log.warning.call_count == warnings


def test_reset_check_is_due_when_the_persisted_time_is_ahead_of_the_clock(firewall):
    # The time is monotonic, so after an Agent restart the persisted one can be ahead of the new clock.
    nothing_new(firewall, last_reset_check=firewall.clock.now + 10_000, newest=log_page([1000]))

    firewall.collect()

    assert len(firewall.backward_jobs()) == 1


def test_reset_check_runs_at_most_every_30_minutes(firewall):
    # The seeded watermark has never been checked (`last_reset_check` 0).
    nothing_new(firewall, newest=log_page([1000]))
    jobs = []

    for minutes in (0, 29, 30):
        firewall.clock.now = 100_000.0 + minutes * 60
        assert firewall.collect() == []
        jobs.append(len(firewall.backward_jobs()))

    # Due on the first pass, not again until 30 minutes after it.
    assert jobs == [1, 1, 2]


def test_a_pass_that_counted_logs_runs_no_reset_check(firewall):
    firewall.answer_forward(1000, log_page([1001]))

    firewall.collect()

    assert firewall.backward_jobs() == []


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
    # The next run submits a new job rather than polling the failed one.
    with pytest.raises(PanosApiError):
        firewall.collect()
    assert len(firewall.submits()) == 2


def test_pages_counted_before_a_job_is_still_active_are_kept(firewall, monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_PAGE_SIZE', 2)
    firewall.answer_forward(1000, log_page([1001, 1002]))
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 2, ACT, ACT, log_page([1003]))

    assert firewall.collect() == []
    samples = firewall.collect()

    assert [p['skip'] for p in firewall.submits()] == ['0', '2']
    assert sum(s.value for s in samples) == 3
    assert firewall.watermark == 1003


def edit_entries(page, edit):
    """`page` with `edit(entry)` applied to each log entry."""
    root = ET.fromstring(page)
    for entry in root.iter('entry'):
        edit(entry)
    return ET.tostring(root)


def test_a_missing_severity_action_subtype_or_vsys_leaves_the_tag_out(firewall):
    def drop(entry):
        for name in ('severity', 'action', 'subtype', 'vsys'):
            entry.remove(entry.find(name))

    page = edit_entries(log_page([1001]), drop)
    firewall.answer_forward(1000, page)

    assert series(firewall.collect()) == {('threat.count', ()): (1, 'count')}


def test_entries_without_a_valid_seqno_are_skipped(firewall):
    def break_seqno(entry):
        if entry.findtext('seqno') == '1002':
            entry.find('seqno').text = 'abc'

    page = edit_entries(log_page([1001, 1002]), break_seqno)
    firewall.answer_forward(1000, page)

    samples = firewall.collect()

    assert sum(s.value for s in samples) == 1


def test_vsys_tag_is_vsys_n(firewall):
    firewall.answer_forward(1000, log_page([1001], vsys='2'))

    assert series(firewall.collect()) == expected({('medium', 'drop', 'spyware', 'vsys2'): 1})


def test_threat_watermark_survives_a_restart_through_the_persistent_cache(dd_run_check, aggregator, fake_panos):
    # The first run has no watermark and starts one below fw-a's capture; a new check instance (an Agent restart)
    # then counts the capture from the persisted watermark, and persists the newest log it read.
    first = THREAT_LOG_FIRST_SEQNO['fw-a']
    fake_panos.answer_log(FW_A_IP, 'backward', None, 0, log_page([first - 1]))
    dd_run_check(new_check())
    assert aggregator.metrics('pan_firewall.threat.count') == []
    fake_panos.recover(FW_A_IP)
    aggregator.reset()

    check = new_check()
    dd_run_check(check)

    assert json.loads(check.read_persistent_cache(CACHE_KEY))['seqno'] == FW_A_LAST_SEQNO


def test_collect_threats_false_makes_no_log_call(dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check(make_instance(collect_threats=False)))

    assert [c for c in fake_panos.calls if c.type == 'log'] == []
    assert aggregator.metrics('pan_firewall.threat.count') == []
