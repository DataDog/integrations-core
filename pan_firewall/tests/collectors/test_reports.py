# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import itertools
from unittest import mock

import pytest

from datadog_checks.pan_firewall import constants
from datadog_checks.pan_firewall.collectors.base import FirewallState
from datadog_checks.pan_firewall.collectors.reports import collect_reports, parse_report, report_params
from datadog_checks.pan_firewall.constants import REPORTS
from datadog_checks.pan_firewall.errors import PanosApiError, PanosUnreachable

from ..common import FW_A_IP, SYNTHETIC
from ..fixture_map import find_report_fixture, report_field
from ..helpers import load_xml, make_ctx, make_instance, new_check, series

pytestmark = pytest.mark.unit

PRIVATE = '10.0.0.0-10.255.255.255'

# The rows (dimension value, sessions, bytes) of fw-a's `report_custom_<field>.xml`, by report.
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
    'top_sources': ('src', [('10.20.2.100', 1158, 136106329), ('10.20.3.100', 324, 184787)]),
    'top_destinations': (
        'dst',
        [
            ('10.20.3.100', 416, 218733),
            ('10.20.2.100', 324, 184787),
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
FIELDS = [field for field, _dimension in REPORTS.values()]
ALL_REPORTS = {f'report:{name}' for name in REPORTS}
PING = ('report:top_applications', 'app:ping')
ACT = SYNTHETIC / 'report_job_act.xml'
# A job polled with one of these answers on every poll of a run: STUCK never finishes, SLOW finishes at the first
# poll of the next run.
STUCK = itertools.repeat('ACT')
SLOW = ['ACT'] * constants.REPORT_JOB_POLLS


def load_report(name):
    field, _dimension = REPORTS[name]
    return load_xml(find_report_fixture(field, 'fw-a'))


def expected_samples(name):
    """The three gauges of each row of the capture: sessions, bytes, and their ratio."""
    dimension, rows = FW_A_ROWS[name]
    expected = {}
    for value, sessions, size in rows:
        tags = (f'report:{name}', f'{dimension}:{value}')
        expected['report.top.sessions', tags] = (sessions, 'gauge')
        expected['report.top.bytes', tags] = (size, 'gauge')
        expected['report.top.bytes_per_session', tags] = (size / sessions, 'gauge')
    return expected


def reported(samples):
    return {tags[0] for _name, tags in series(samples)}


@pytest.mark.parametrize('name', list(REPORTS))
def test_report_of_the_capture(name):
    assert series(parse_report(load_report(name), name)) == expected_samples(name)


def test_bytes_per_session_is_zero_without_sessions():
    root = load_report('top_applications')
    root.find('result/report/entry/sessions').text = '0'

    assert series(parse_report(root, 'top_applications'))['report.top.bytes_per_session', PING] == (0, 'gauge')


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


def test_job_asks_for_the_top_n_of_the_last_24_hours():
    assert report_params('app', 5) == {
        'type': 'report',
        'reporttype': 'dynamic',
        'reportname': 'custom-dynamic-report',
        'async': 'yes',
        'cmd': (
            '<type><trsum><sortby>sessions</sortby><aggregate-by><member>app</member></aggregate-by>'
            '<values><member>sessions</member><member>bytes</member></values></trsum></type>'
            '<period>last-24-hrs</period><topn>5</topn><topm>10</topm><caption>datadog</caption>'
        ),
    }


class ScriptedClient:
    """Stands in for `PanosClient` to the reports collector. A job's id is its report field; each poll of it answers
    the next item of `script[field]`, a status or an exception to raise, then FIN with the capture."""

    def __init__(self, script=None):
        self.script = {field: iter(answers) for field, answers in (script or {}).items()}
        self.events = []
        self.cmds = []

    def submit_job(self, params):
        field = report_field(params['cmd'])
        self.events.append(('submit', field))
        self.cmds.append(params['cmd'])
        return field

    def get_job(self, job_type, job_id):
        self.events.append(('get', job_id))
        answer = next(self.script.get(job_id, iter(())), 'FIN')
        if isinstance(answer, Exception):
            raise answer
        return answer, load_xml(find_report_fixture(job_id, 'fw-a') if answer == 'FIN' else ACT)

    @property
    def submitted(self):
        return [field for kind, field in self.events if kind == 'submit']


def run(client, state=None, top_n=None):
    ctx = make_ctx(state=state, config=mock.Mock(report_top_n=top_n))
    ctx.client = client
    return collect_reports(ctx)


@pytest.fixture(autouse=True)
def no_poll_delay(monkeypatch):
    monkeypatch.setattr(constants, 'REPORT_JOB_POLL_DELAY', 0)


def test_the_jobs_run_one_at_a_time_in_report_order():
    client = ScriptedClient()

    run(client)

    assert client.events == [event for field in FIELDS for event in (('submit', field), ('get', field))]


@pytest.mark.parametrize('top_n, expected', [(None, 10), (7, 7)])
def test_the_job_is_asked_for_the_configured_top_n_or_ten(top_n, expected):
    client = ScriptedClient()

    run(client, top_n=top_n)

    assert all(f'<topn>{expected}</topn>' in cmd for cmd in client.cmds)


def test_a_job_still_running_after_ten_polls_is_carried_over_and_not_resubmitted():
    client = ScriptedClient({'app': SLOW})
    state = FirewallState()

    assert run(client, state) == []
    assert client.events == [('submit', 'app')] + [('get', 'app')] * constants.REPORT_JOB_POLLS

    samples = run(client, state)

    assert client.submitted == FIELDS
    assert series(samples) == {key: value for name in REPORTS for key, value in expected_samples(name).items()}


def test_a_job_that_never_finishes_is_dropped_after_three_carry_overs_so_the_others_are_reported():
    client = ScriptedClient({'app': STUCK})
    state = FirewallState()

    for _ in range(constants.REPORT_MAX_CARRIES + 1):
        samples = run(client, state)

    assert reported(samples) == ALL_REPORTS - {'report:top_applications'}
    assert client.submitted.count('app') == 1


@pytest.mark.parametrize(
    'answer', [pytest.param('FAIL', id='failed'), pytest.param(PanosApiError('400', 'bad job'), id='api-error')]
)
def test_a_job_that_fails_is_skipped_and_the_other_reports_still_run(answer):
    client = ScriptedClient({'src': [answer]})

    assert reported(run(client)) == ALL_REPORTS - {'report:top_sources'}


def test_slow_jobs_do_not_starve_the_reports_after_them():
    client = ScriptedClient(dict.fromkeys(FIELDS, SLOW))
    state = FirewallState()

    samples = [sample for _run in range(len(REPORTS) + 1) for sample in run(client, state)]

    # One cycle of the ten reports, each submitted once, before any is submitted again.
    assert reported(samples) == ALL_REPORTS
    assert client.submitted == FIELDS


def test_a_timeout_polling_a_carried_job_keeps_it_for_the_next_run():
    client = ScriptedClient({'app': [*SLOW, PanosUnreachable('slow')]})
    state = FirewallState()
    run(client, state)

    with pytest.raises(PanosUnreachable):
        run(client, state)
    samples = run(client, state)

    assert client.submitted.count('app') == 1
    assert ('report.top.sessions', PING) in series(samples)


def test_an_api_error_polling_a_carried_job_drops_it_and_the_run_goes_on_with_the_next_report():
    client = ScriptedClient({'app': [*SLOW, PanosApiError('400', 'bad job')]})
    state = FirewallState()
    run(client, state)

    samples = run(client, state)

    assert client.submitted == FIELDS
    assert reported(samples) == ALL_REPORTS - {'report:top_applications'}


def test_a_timeout_submitting_a_job_propagates_and_the_next_run_submits_the_same_report():
    client = ScriptedClient()
    state = FirewallState()
    submit = client.submit_job
    client.submit_job = mock.Mock(side_effect=[submit(report_params('app', 10)), PanosUnreachable('slow')])

    with pytest.raises(PanosUnreachable):
        run(client, state)
    client.submit_job = submit
    run(client, state)

    # The report whose submit timed out (the second) is not skipped.
    assert client.submitted == FIELDS


def report_calls(fake_panos):
    return [c for c in fake_panos.calls if c.type == 'report']


def test_slow_firewall_is_polled_every_run_until_all_reports_are_collected_then_every_30_minutes(
    dd_run_check, aggregator, fake_panos, schedule_clock
):
    for field in FIELDS:
        fake_panos.answer_report(
            FW_A_IP, field, *[ACT] * constants.REPORT_JOB_POLLS, find_report_fixture(field, 'fw-a')
        )
    check = new_check(make_instance(collect_reports=True))

    # One report per run (a job finishes at the first poll of the next run), 60 s apart, never 30 minutes.
    for _run in range(len(REPORTS) + 1):
        dd_run_check(check)
        schedule_clock.now += 60

    sent = {
        t for m in aggregator.metrics('pan_firewall.report.top.sessions') for t in m.tags if t.startswith('report:')
    }
    assert sent == ALL_REPORTS
    calls = len(report_calls(fake_panos))

    dd_run_check(check)

    assert len(report_calls(fake_panos)) == calls

    # 30 minutes later the cycle starts again from the first report.
    schedule_clock.now += 1800
    dd_run_check(check)

    submits = [c for c in report_calls(fake_panos)[calls:] if c.action is None]
    assert submits and submits[0].params['cmd'] == report_calls(fake_panos)[0].params['cmd']
