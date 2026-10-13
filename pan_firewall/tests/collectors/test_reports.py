# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from unittest import mock

import pytest

from datadog_checks.pan_firewall import constants
from datadog_checks.pan_firewall import poller as poller_module
from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.reports import collect_reports, parse_report, report_params
from datadog_checks.pan_firewall.constants import REPORTS
from datadog_checks.pan_firewall.errors import PanosTimeout
from datadog_checks.pan_firewall.scheduler import FirewallSchedule
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FIXTURES
from ..fixture_map import find_report_fixture
from ..test_check import FW_A_TAGS, make_instance, new_check

SYNTHETIC = FIXTURES / 'synthetic'
PRIVATE = '10.0.0.0-10.255.255.255'

# The rows (dimension value, sessions, bytes) of each capture's `report_custom_<field>.xml`, by report.
FW_A_ROWS = {
    'top_applications': (
        'app',
        [
            ('ping', 536, 105056),
            ('ssl', 262, 79433373),
            ('web-browsing', 260, 3498139),
            ('dns-base', 228, 42643),
            ('google-base', 52, 5213825),
        ],
    ),
    'top_application_categories': (
        'app_category',
        [
            ('general-internet', 848, 8817020),
            ('networking', 530, 79483216),
            ('business-systems', 104, 47990880),
        ],
    ),
    'top_technology_categories': (
        'app_technology',
        [
            ('network-protocol', 804, 154899),
            ('browser-based', 626, 103473416),
            ('client-server', 52, 32662801),
        ],
    ),
    'top_sources': ('src', [('10.60.2.100', 1158, 136106329), ('10.60.3.100', 324, 184787)]),
    'top_destinations': (
        'dst',
        [
            ('10.60.3.100', 416, 218733),
            ('10.60.2.100', 324, 184787),
            ('8.8.8.8', 231, 43231),
            ('208.80.154.224', 52, 5703421),
            ('146.75.76.81', 52, 42926114),
        ],
    ),
    'top_source_countries': ('src_country', [(PRIVATE, 1482, 136291116)]),
    'top_destination_countries': (
        'dst_country',
        [(PRIVATE, 740, 403520), ('United States', 690, 133514055), ('Japan', 52, 2373541)],
    ),
    'top_ingress_zones': ('src_zone', [('trust', 1158, 136106329), ('vpn', 324, 184787)]),
    'top_egress_zones': ('dst_zone', [('untrust', 742, 135887596), ('vpn', 416, 218733), ('trust', 324, 184787)]),
    'top_rules': (
        'rule',
        [('trust-out', 742, 135887596), ('trust-to-vpn', 416, 218733), ('vpn-to-trust', 324, 184787)],
    ),
}
FW_B_ROWS = {
    'top_applications': (
        'app',
        [
            ('ping', 533, 104468),
            ('ssl', 267, 80983096),
            ('web-browsing', 263, 3499357),
            ('dns-base', 227, 42668),
            ('google-base', 53, 5313702),
        ],
    ),
    'top_application_categories': (
        'app_category',
        [
            ('general-internet', 849, 8917527),
            ('networking', 534, 81032964),
            ('business-systems', 106, 48921262),
        ],
    ),
    'top_technology_categories': (
        'app_technology',
        [
            ('network-protocol', 800, 154336),
            ('browser-based', 636, 105421861),
            ('client-server', 53, 33295556),
        ],
    ),
    'top_sources': ('src', [('10.60.3.100', 1173, 138691120), ('10.60.2.100', 316, 180633)]),
    'top_destinations': (
        'dst',
        [
            ('10.60.2.100', 426, 223649),
            ('10.60.3.100', 316, 180633),
            ('8.8.8.8', 227, 42668),
            ('208.80.154.224', 53, 5813716),
            ('146.75.76.81', 53, 43764204),
        ],
    ),
    'top_source_countries': ('src_country', [(PRIVATE, 1489, 138871753)]),
    'top_destination_countries': (
        'dst_country',
        [(PRIVATE, 742, 404282), ('United States', 694, 136046024), ('Japan', 53, 2421447)],
    ),
    'top_ingress_zones': ('src_zone', [('trust', 1173, 138691120), ('vpn', 316, 180633)]),
    'top_egress_zones': ('dst_zone', [('untrust', 747, 138467471), ('vpn', 426, 223649), ('trust', 316, 180633)]),
    'top_rules': (
        'rule',
        [('trust-out', 747, 138467471), ('trust-to-vpn', 426, 223649), ('vpn-to-trust', 316, 180633)],
    ),
}
ROWS = {'fw-a': FW_A_ROWS, 'fw-b': FW_B_ROWS}


def load_report(name, firewall='fw-a'):
    field, _tag = REPORTS[name]
    response, _submit = find_report_fixture(field, firewall)
    return parse_response(response.read_bytes())


def expected_samples(name, expected_rows):
    """The three gauges of each row: sessions, bytes, and their ratio (0 without sessions)."""
    dimension, rows = expected_rows
    expected = {}
    for value, sessions, size in rows:
        tags = (f'report:{name}', f'{dimension}:{value}')
        expected['report.top.sessions', tags] = sessions
        expected['report.top.bytes', tags] = size
        expected['report.top.bytes_per_session', tags] = size / sessions if sessions else 0
    return expected


def series(samples):
    """Samples keyed by (name, tags) to value; every one is a gauge. Fails on a duplicate series."""
    assert {s.kind for s in samples} <= {'gauge'}
    result = {(s.name, s.tags): s.value for s in samples}
    assert len(result) == len(samples)
    return result


@pytest.mark.parametrize('firewall', ['fw-a', 'fw-b'])
@pytest.mark.parametrize('name', list(REPORTS))
def test_report_of_the_captures(name, firewall):
    samples = parse_report(load_report(name, firewall), name)

    assert series(samples) == expected_samples(name, ROWS[firewall][name])


def test_bytes_per_session_is_the_average_and_zero_without_sessions():
    root = load_report('top_applications')
    ping = ('report:top_applications', 'app:ping')
    assert series(parse_report(root, 'top_applications'))['report.top.bytes_per_session', ping] == 196.0

    root.find('result/report/entry/sessions').text = '0'
    values = series(parse_report(root, 'top_applications'))

    assert values['report.top.sessions', ping] == 0
    assert values['report.top.bytes', ping] == 105056
    assert values['report.top.bytes_per_session', ping] == 0


def test_a_row_without_its_dimension_or_numbers_is_skipped():
    root = load_report('top_applications')
    first, second, third, *_ = root.findall('result/report/entry')
    first.remove(first.find('app'))
    second.remove(second.find('bytes'))
    third.find('sessions').text = 'n/a'

    assert {tags[1] for _name, tags in series(parse_report(root, 'top_applications'))} == {
        'app:dns-base',
        'app:google-base',
    }


def test_private_country_range_is_kept_raw():
    samples = parse_report(load_report('top_source_countries'), 'top_source_countries')

    assert ('report:top_source_countries', f'src_country:{PRIVATE}') in {s.tags for s in samples}


def test_job_asks_for_the_top_n_of_the_last_24_hours():
    params = report_params('app', 5)

    assert params['type'] == 'report'
    assert params['reporttype'] == 'dynamic'
    assert params['reportname'] == 'custom-dynamic-report'
    assert params['cmd'] == (
        '<type><trsum><sortby>sessions</sortby><aggregate-by><member>app</member></aggregate-by>'
        '<values><member>sessions</member><member>bytes</member></values></trsum></type>'
        '<period>last-24-hrs</period><topn>5</topn><topm>10</topm><caption>datadog</caption>'
    )


def make_context(client, state=None, top_n=None):
    return CollectContext(
        client=client,
        identity=mock.Mock(),
        state=state or FirewallState(),
        config=mock.Mock(report_top_n=top_n),
        log=mock.Mock(),
    )


def field_of(params):
    return re.search(r'<aggregate-by><member>([^<]+)</member>', params['cmd']).group(1)


class ScriptedClient:
    """Stands in for `PanosClient` to the reports collector: it opens report jobs and answers their polls from the
    captures.

    `act_polls` maps a report field to how many polls of each of its jobs answer ACT before FIN (a huge number never
    finishes), `failing` lists the fields whose jobs answer FAIL, and `timeout` makes every poll raise PanosTimeout.
    """

    def __init__(self, act_polls=None, failing=(), firewall='fw-a'):
        self.act_polls = dict(act_polls or {})
        self.failing = set(failing)
        self.timeout = False
        self.firewall = firewall
        self.events = []
        self._fields = {}
        self._polls = {}

    def submit_job(self, params):
        field = field_of(params)
        job_id = f'job-{len(self._fields) + 1}'
        self._fields[job_id] = field
        self._polls[job_id] = 0
        self.events.append(('submit', field, params))
        return job_id

    def get_job(self, job_type, job_id):
        assert job_type == 'report'
        if self.timeout:
            raise PanosTimeout('slow')
        field = self._fields[job_id]
        self.events.append(('get', field, job_id))
        self._polls[job_id] += 1
        response, _submit = find_report_fixture(field, self.firewall)
        if field in self.failing:
            return 'FAIL', parse_response(response.read_bytes())
        if self._polls[job_id] <= self.act_polls.get(field, 0):
            return 'ACT', parse_response((SYNTHETIC / 'report_job_act.xml').read_bytes())
        return 'FIN', parse_response(response.read_bytes())

    def submitted(self):
        return [field for kind, field, *_ in self.events if kind == 'submit']

    def polls(self, field):
        return sum(1 for kind, f, *_ in self.events if kind == 'get' and f == field)


STUCK = 10**6
SLOW = constants.REPORT_JOB_POLLS  # ACT on every poll of the run that submits the job, FIN on the next run's first


@pytest.fixture(autouse=True)
def no_poll_delay(monkeypatch):
    monkeypatch.setattr(constants, 'REPORT_JOB_POLL_DELAY', 0)


def test_the_jobs_run_one_at_a_time_and_none_aggregates_by_app_twice():
    client = ScriptedClient()

    samples = collect_reports(make_context(client))

    # Each job is polled to its end before the next is submitted: submit, get, submit, get, ...
    assert [kind for kind, *_ in client.events] == ['submit', 'get'] * 10
    fields = client.submitted()
    assert fields == [field for field, _tag in REPORTS.values()]
    assert fields.count('app') == 1
    assert len(samples) == 3 * sum(len(rows) for _tag, rows in FW_A_ROWS.values())


@pytest.mark.parametrize('top_n, expected', [(None, '10'), (7, '7')])
def test_the_job_is_asked_for_the_configured_top_n_or_ten(top_n, expected):
    client = ScriptedClient()

    collect_reports(make_context(client, top_n=top_n))

    topn = {
        re.search(r'<topn>(\d+)</topn>', params['cmd']).group(1)
        for kind, _f, params in client.events
        if kind == 'submit'
    }
    assert topn == {expected}


def test_a_job_still_running_after_ten_polls_is_carried_over_and_not_resubmitted():
    client = ScriptedClient(act_polls={'app': STUCK})
    state = FirewallState()

    # The first report never finishes: the run polls it 10 times, submits nothing else, and reports nothing.
    assert collect_reports(make_context(client, state)) == []
    assert client.polls('app') == 10
    assert client.submitted() == ['app']

    # The next run polls the same job first; it has finished, and the other nine reports follow.
    client.act_polls.clear()
    samples = collect_reports(make_context(client, state))

    assert client.submitted().count('app') == 1
    assert client.polls('app') == 11
    assert client.submitted()[1:] == [field for name, (field, _tag) in REPORTS.items() if field != 'app']
    assert series(samples) == {
        key: value for name, rows in FW_A_ROWS.items() for key, value in expected_samples(name, rows).items()
    }


def test_a_job_that_never_finishes_is_dropped_after_three_carry_overs_so_the_others_are_reported():
    client = ScriptedClient(act_polls={'app': STUCK})
    state = FirewallState()
    warnings = []

    for _ in range(constants.REPORT_MAX_CARRIES + 1):
        ctx = make_context(client, state)
        samples = collect_reports(ctx)
        warnings.append(ctx.log.warning.call_count)

    # Runs 1 to 3 carry the job; run 4 gives up on it, warns, and reports the other nine reports (the app report is
    # submitted again by the next run).
    assert warnings == [0, 0, 0, 1]
    assert {tags[0] for _name, tags in series(samples)} == {f'report:{n}' for n in REPORTS} - {
        'report:top_applications'
    }
    assert client.submitted().count('app') == 1


def test_a_failed_job_is_skipped_with_one_warning_and_the_other_reports_still_run():
    client = ScriptedClient(failing={'src'})
    state = FirewallState()
    ctx = make_context(client, state)

    samples = collect_reports(ctx)

    assert {tags[0] for _name, tags in series(samples)} == {f'report:{n}' for n in REPORTS} - {'report:top_sources'}
    ctx.log.warning.assert_called_once()
    collect_reports(second := make_context(client, state))
    second.log.warning.assert_not_called()


def test_slow_jobs_do_not_starve_the_reports_after_them():
    # Every job is still running at the end of the run that submits it and done at the next one's first poll.
    client = ScriptedClient(act_polls={field: SLOW for field, _tag in REPORTS.values()})
    state = FirewallState()
    reported = set()
    submitted_per_run = []

    for _run in range(len(REPORTS) + 1):
        ctx = make_context(client, state)
        reported |= {tags[0] for _name, tags in series(collect_reports(ctx))}
        submitted_per_run.append(len(client.submitted()))

    # One cycle of the ten reports, each submitted once, before any is submitted again.
    assert reported == {f'report:{name}' for name in REPORTS}
    assert client.submitted() == [field for field, _tag in REPORTS.values()]
    assert submitted_per_run == list(range(1, len(REPORTS) + 1)) + [len(REPORTS)]


def test_a_carried_job_keeps_the_reports_collector_due_until_the_cycle_is_done():
    client = ScriptedClient(act_polls={'app': SLOW})
    state = FirewallState()

    first = make_context(client, state)
    collect_reports(first)
    assert 'reports' in first.state.still_due

    # The next run finishes the job and the rest of the cycle: nothing is left to poll.
    state.still_due.clear()
    collect_reports(make_context(client, state))
    assert 'reports' not in state.still_due


def test_a_timeout_polling_a_carried_job_keeps_it_for_the_next_run():
    client = ScriptedClient(act_polls={'app': SLOW})
    state = FirewallState()
    collect_reports(make_context(client, state))
    carried = state.reports.pending
    client.timeout = True

    with pytest.raises(PanosTimeout):
        collect_reports(make_context(client, state))

    assert state.reports.pending is carried
    client.timeout = False
    samples = collect_reports(make_context(client, state))
    assert client.submitted().count('app') == 1
    assert ('report.top.sessions', ('report:top_applications', 'app:ping')) in series(samples)


def test_a_timeout_submitting_a_job_propagates():
    client = mock.Mock()
    client.submit_job.side_effect = PanosTimeout('slow')
    state = FirewallState()

    with pytest.raises(PanosTimeout):
        collect_reports(make_context(client, state))

    assert state.reports.pending is None


def report_calls(fake_panos):
    return [c for c in fake_panos.calls if c.type == 'report']


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(poller_module, 'FirewallSchedule', lambda: FirewallSchedule(lambda: now[0]))
    return now


def test_slow_firewall_is_polled_every_run_until_all_reports_are_collected_then_every_30_minutes(
    real_collectors, dd_run_check, aggregator, fake_panos, clock
):
    act = SYNTHETIC / 'report_job_act.xml'
    for field, _tag in REPORTS.values():
        response, _submit = find_report_fixture(field, 'fw-a')
        fake_panos.answer_report('192.0.2.10', field, *[act] * constants.REPORT_JOB_POLLS, response)
    check = new_check(make_instance(collect_reports=True))

    # One report per run (a job finishes at the first poll of the next run), 60 s apart, never 30 minutes.
    for _run in range(len(REPORTS) + 1):
        dd_run_check(check)
        clock[0] += 60

    for name, rows in FW_A_ROWS.items():
        for (metric, tags), value in expected_samples(name, rows).items():
            aggregator.assert_metric(
                f'pan_firewall.{metric}', value, tags=sorted([*FW_A_TAGS, *tags]), metric_type=aggregator.GAUGE
            )
    calls = len(report_calls(fake_panos))

    dd_run_check(check)

    assert len(report_calls(fake_panos)) == calls


def test_reports_are_registered_and_submit_through_the_check_when_enabled(
    real_collectors, dd_run_check, aggregator, fake_panos
):
    assert 'reports' in COLLECT_FUNCTIONS

    dd_run_check(new_check(make_instance(collect_reports=True)))

    total = 0
    for name, rows in FW_A_ROWS.items():
        for (metric, tags), value in expected_samples(name, rows).items():
            aggregator.assert_metric(
                f'pan_firewall.{metric}', value, tags=sorted([*FW_A_TAGS, *tags]), metric_type=aggregator.GAUGE
            )
            total += 1
    assert total == 90
    for metric in ('sessions', 'bytes', 'bytes_per_session'):
        assert len(aggregator.metrics(f'pan_firewall.report.top.{metric}')) == 30
    submits = [c for c in report_calls(fake_panos) if c.action is None]
    assert len(submits) == 10
    assert len({field_of(c.params) for c in submits}) == 10
    assert all('<topn>10</topn>' in c.params['cmd'] for c in submits)


@pytest.mark.parametrize('options', [{}, {'collect_reports': False}])
def test_reports_are_not_called_unless_enabled(options, real_collectors, dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check(make_instance(**options)))

    assert report_calls(fake_panos) == []
    assert not aggregator.metrics('pan_firewall.report.top.sessions')
