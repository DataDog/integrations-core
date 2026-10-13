# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
from collections import Counter
from types import SimpleNamespace
from unittest import mock
from xml.etree import ElementTree as ET

import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.pan_firewall import constants
from datadog_checks.pan_firewall.api import PanosClient, api_url
from datadog_checks.pan_firewall.auth import Credentials, KeyManager
from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.threats import collect_threats
from datadog_checks.pan_firewall.errors import PanosApiError

from ..common import FIXTURES
from ..fixture_map import (
    BACKWARD_NEWEST_SEQNO,
    PROBE_SEQNO_PAGE_SIZE,
    PROBE_SEQNO_PAGES,
    PROBE_SEQNO_START,
    THREAT_LOG_FIRST_SEQNO,
    seqno_query,
)
from ..test_check import FW_A_IP, FW_A_SERIAL, FW_A_TAGS, make_instance, new_check

SYNTHETIC = FIXTURES / 'synthetic'
CACHE_KEY = f'threat_watermark:{FW_A_SERIAL}'
FW_A_LAST_SEQNO = 7691899338913481002
PROBE_LAST_SEQNO = 7691899338913582049
PROBE_ENTRIES = 19 * PROBE_SEQNO_PAGE_SIZE + 5
EMPTY = (SYNTHETIC / 'threat_log_empty.xml').read_bytes()
ACT = (SYNTHETIC / 'threat_log_act.xml').read_bytes()
CLOCK_BACK = SYNTHETIC / 'threat_log_clock_back.xml'
NEWEST_AFTER_RESET = SYNTHETIC / 'threat_log_newest_after_reset.xml'
NO_CAPTURE = (200, b'<response status="error" code="400"><msg><line>no capture</line></msg></response>')
# What fw-a's and fw-b's `threat_log_5m.xml` hold: (severity, action, subtype, vsys) -> logs. 39 logs each.
CAPTURE_COUNTS = {
    ('medium', 'drop', 'spyware', 'vsys1'): 22,
    ('critical', 'reset-both', 'vulnerability', 'vsys1'): 8,
    ('medium', 'reset-both', 'vulnerability', 'vsys1'): 8,
    ('medium', 'drop-packet', 'spyware', 'vsys1'): 1,
}
POLL_ENTRY = ET.parse(CLOCK_BACK).getroot().find('result/log/logs/entry')


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_JOB_POLLS', 2)
    monkeypatch.setattr(constants, 'THREAT_JOB_POLL_DELAY', 0)


class Clock:
    def __init__(self, now=100_000.0):
        self.now = now

    def __call__(self):
        return self.now


class Context:
    """A firewall's threats collector as the poller runs it: a real client on the fake transport, and a cache."""

    def __init__(self, fake_panos, cache=None, clock=None, host=FW_A_IP):
        self.fake = fake_panos
        self.cache = {} if cache is None else cache
        self.clock = clock or Clock()
        self.host = host
        self.log = mock.Mock()
        self.restart()

    def restart(self):
        """New in-memory state over the same cache, as after an Agent restart."""
        log = self.log
        http = RequestsWrapper({}, {}, {}, log)
        keys = KeyManager(http, api_url(self.host, 443), Credentials(username=None, password=None, api_key='key'))
        self.ctx = CollectContext(
            client=PanosClient(http, self.host, 443, keys, log),
            identity=SimpleNamespace(serial=FW_A_SERIAL),
            state=FirewallState(),
            config=mock.Mock(),
            log=log,
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

    def submits(self):
        return [c.params for c in self.fake.calls_to(self.host) if c.type == 'log' and c.action is None]

    def backward_jobs(self):
        return [p for p in self.submits() if p['dir'] == 'backward']


@pytest.fixture
def firewall(fake_panos):
    return Context(fake_panos)


def series(samples):
    result = {(s.name, s.tags, s.kind): s.value for s in samples}
    assert len(result) == len(samples)
    return result


def tags(severity, action, subtype, vsys):
    return (f'severity:{severity}', f'action:{action}', f'subtype:{subtype}', f'vsys:{vsys}')


def expected(counts):
    return {('threat.count', tags(*key), 'count'): n for key, n in counts.items()}


def log_page(seqnos, **fields):
    """A finished log job of one entry per seqno, copied from a real entry of `synthetic/threat_log_clock_back.xml`."""
    entries = []
    for seqno in seqnos:
        entry = copy.deepcopy(POLL_ENTRY)
        entry.find('seqno').text = str(seqno)
        for name, value in fields.items():
            entry.find(name).text = value
        entries.append(ET.tostring(entry, encoding='unicode'))
    return (
        '<response status="success"><result><job><status>FIN</status><id>1</id></job>'
        f'<log><logs count="{len(entries)}" progress="100">{"".join(entries)}</logs></log></result></response>'
    ).encode()


def probe_counts():
    """Tag counts and seqnos of the `probe-seqno` pages, read from the fixtures."""
    counts, seqnos = Counter(), []
    for page in range(PROBE_SEQNO_PAGES):
        root = ET.parse(FIXTURES / 'probe-seqno' / f'seq_0_p{page}.xml').getroot()
        for entry in root.iterfind('result/log/logs/entry'):
            counts[tuple(entry.findtext(f) for f in ('severity', 'action', 'subtype', 'vsys'))] += 1
            seqnos.append(int(entry.findtext('seqno')))
    return counts, seqnos


@pytest.mark.parametrize('name', ['fw-a', 'fw-b'])
def test_threat_logs_of_the_captures_are_counted_by_tag(fake_panos, name):
    host = '192.0.2.10' if name == 'fw-a' else '192.0.2.11'
    ctx = Context(fake_panos, host=host)
    first = THREAT_LOG_FIRST_SEQNO[name]
    ctx.seed(first - 1)

    samples = ctx.collect()

    assert series(samples) == expected(CAPTURE_COUNTS)
    assert sum(s.value for s in samples) == 39
    assert all(len(s.tags) == 4 and not any(t.startswith('window') for t in s.tags) for s in samples)


def test_request_is_a_seqno_query_without_receive_time(firewall):
    firewall.seed(THREAT_LOG_FIRST_SEQNO['fw-a'] - 1)

    firewall.collect()

    (params,) = firewall.submits()
    assert params == {
        'type': 'log',
        'log-type': 'threat',
        'dir': 'forward',
        'nlogs': '5000',
        'skip': '0',
        'query': f'(seqno geq {THREAT_LOG_FIRST_SEQNO["fw-a"]})',
    }
    assert 'receive_time' not in ' '.join(params.values())


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
    assert len(seqnos) == len(set(seqnos)) == PROBE_ENTRIES == 385
    assert series(samples) == expected(counts)
    assert sum(s.value for s in samples) == 385
    assert firewall.watermark == PROBE_LAST_SEQNO == max(seqnos)


def test_each_finished_page_is_read_with_one_request(firewall, monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_PAGE_SIZE', PROBE_SEQNO_PAGE_SIZE)
    firewall.seed(PROBE_SEQNO_START - 1)

    firewall.collect()

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
    firewall.seed(1000)
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 0, log_page([999, 1000, 1001, 1003]))

    samples = firewall.collect()

    assert series(samples) == expected({('medium', 'drop', 'spyware', 'vsys1'): 2})
    assert firewall.watermark == 1003


def test_a_full_page_of_5000_asks_for_the_next_one(firewall):
    firewall.seed(1000)
    first = log_page(range(1001, 6001))
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 0, first)
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
    assert firewall.cache[CACHE_KEY] == json.dumps({'seqno': PROBE_SEQNO_START - 1, 'last_reset_check': 0.0})
    firewall.fake.recover(FW_A_IP)
    firewall.fake.calls.clear()
    samples = firewall.collect()
    assert sum(s.value for s in samples) == PROBE_ENTRIES
    assert firewall.submits()[0]['skip'] == '0'
    assert firewall.watermark == PROBE_LAST_SEQNO


def test_clock_going_back_counts_every_log_once_with_no_warning_or_extra_job(firewall):
    firewall.seed(1000)
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 0, CLOCK_BACK)

    samples = firewall.collect()

    assert series(samples) == expected({('medium', 'drop', 'spyware', 'vsys1'): 30})
    assert firewall.watermark == 1030
    assert len(firewall.submits()) == 1
    firewall.ctx.log.warning.assert_not_called()


def nothing_new(firewall, watermark=1000, last_reset_check=0.0, newest=None):
    firewall.seed(watermark, last_reset_check)
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(watermark + 1), 0, EMPTY)
    if newest is not None:
        firewall.fake.answer_log(FW_A_IP, 'backward', None, 0, newest)


def test_seqno_reset_rebaselines_the_watermark_and_warns_once(firewall):
    nothing_new(firewall, newest=NEWEST_AFTER_RESET)

    assert firewall.collect() == []

    assert firewall.watermark == 12
    assert len(firewall.backward_jobs()) == 1
    firewall.ctx.log.warning.assert_called_once()


def test_newest_seqno_equal_to_the_watermark_changes_nothing(firewall):
    nothing_new(firewall, watermark=12, newest=NEWEST_AFTER_RESET)

    assert firewall.collect() == []

    assert firewall.watermark == 12
    assert len(firewall.backward_jobs()) == 1
    firewall.ctx.log.warning.assert_not_called()


def test_reset_check_runs_at_most_every_30_minutes(firewall):
    nothing_new(firewall, newest=log_page([1000]))

    for minutes in (0, 5, 29, 30):
        firewall.clock.now = 100_000.0 + minutes * 60
        firewall.collect()

    # Due on the first pass (never checked), not again until 30 minutes after it, then due again.
    assert len(firewall.backward_jobs()) == 2


def test_reset_check_is_due_when_the_persisted_time_is_ahead_of_the_clock(firewall):
    # The time is monotonic, so after an Agent restart the persisted one can be ahead of the new clock.
    nothing_new(firewall, last_reset_check=firewall.clock.now + 10_000, newest=log_page([1000]))

    firewall.collect()

    assert len(firewall.backward_jobs()) == 1


def test_a_pass_that_counted_logs_runs_no_reset_check(firewall):
    firewall.seed(1000)
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 0, log_page([1001]))

    firewall.collect()

    assert firewall.backward_jobs() == []


def test_job_still_active_is_polled_next_run_without_resubmitting(firewall):
    firewall.seed(1000)
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 0, ACT, ACT, log_page([1001, 1002]))

    assert firewall.collect() == []
    assert firewall.watermark == 1000
    samples = firewall.collect()

    assert len(firewall.submits()) == 1
    assert sum(s.value for s in samples) == 2
    assert firewall.watermark == 1002


def test_pages_counted_before_a_job_is_still_active_are_kept(firewall, monkeypatch):
    monkeypatch.setattr(constants, 'THREAT_PAGE_SIZE', 2)
    firewall.seed(1000)
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 0, log_page([1001, 1002]))
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 2, ACT, ACT, log_page([1003]))

    assert firewall.collect() == []
    samples = firewall.collect()

    assert [p['skip'] for p in firewall.submits()] == ['0', '2']
    assert sum(s.value for s in samples) == 3
    assert firewall.watermark == 1003


def test_vsys_tag_is_vsys_n(firewall):
    firewall.seed(1000)
    firewall.fake.answer_log(FW_A_IP, 'forward', seqno_query(1001), 0, log_page([1001], vsys='2'))

    assert series(firewall.collect()) == expected({('medium', 'drop', 'spyware', 'vsys2'): 1})


def test_threats_are_registered_and_submit_through_the_check(real_collectors, dd_run_check, aggregator, fake_panos):
    assert 'threats' in COLLECT_FUNCTIONS
    # The first run has no watermark and starts one below fw-a's capture; a new check instance (an Agent restart)
    # then counts the capture from the persisted watermark.
    first = THREAT_LOG_FIRST_SEQNO['fw-a']
    fake_panos.answer_log(FW_A_IP, 'backward', None, 0, log_page([first - 1]))
    dd_run_check(new_check())
    assert aggregator.metrics('pan_firewall.threat.count') == []
    fake_panos.recover(FW_A_IP)
    aggregator.reset()

    check = new_check()
    dd_run_check(check)

    for (severity, action, subtype, vsys), count in CAPTURE_COUNTS.items():
        aggregator.assert_metric(
            'pan_firewall.threat.count',
            count,
            tags=sorted([*FW_A_TAGS, *tags(severity, action, subtype, vsys)]),
            metric_type=aggregator.COUNT,
        )
    assert len(aggregator.metrics('pan_firewall.threat.count')) == 4
    assert json.loads(check.read_persistent_cache(CACHE_KEY))['seqno'] == FW_A_LAST_SEQNO


def test_collect_threats_false_makes_no_log_call(real_collectors, dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check(make_instance(collect_threats=False)))

    assert [c for c in fake_panos.calls if c.type == 'log'] == []
    assert aggregator.metrics('pan_firewall.threat.count') == []
