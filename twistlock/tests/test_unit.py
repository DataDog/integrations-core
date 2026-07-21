# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from datetime import datetime, timedelta, timezone

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.twistlock import TwistlockCheck
from datadog_checks.twistlock.config import Config

pytestmark = pytest.mark.unit


class FrozenDateTime(datetime):
    FIXED_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.FIXED_NOW if tz is None else cls.FIXED_NOW.astimezone(tz)


def make_vuln(cve_id, published):
    return {'id': cve_id, 'description': 'a description', 'published': int(published.timestamp())}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_config_strips_single_trailing_slash():
    # Kills the core/ReplaceUnaryOperator_Delete_Not, core/AddNot, and core/NumberReplacer
    # mutants at config.py:11-12 (the `if self.url.endswith('/'): self.url = self.url[:-1]` block).
    config = Config({'url': 'http://localhost:8081/'})
    assert config.url == 'http://localhost:8081'


def test_config_leaves_url_without_trailing_slash_untouched():
    # Kills the core/ReplaceUnaryOperator_Delete_Not mutant at config.py:11 (removing the `not`
    # would make the endswith check always negate, stripping a character from every URL).
    config = Config({'url': 'http://localhost:8081'})
    assert config.url == 'http://localhost:8081'


def test_config_appends_project_tag_when_project_set():
    # Kills the core/AddNot mutant at config.py:19 (`if self.project:` -> `if not self.project:`).
    config = Config({'url': 'http://localhost:8081', 'project': 'my-project', 'tags': []})
    assert 'project:my-project' in config.tags


def test_config_does_not_append_project_tag_when_project_unset():
    # Kills the core/AddNot mutant at config.py:19 in the other direction, which would append a
    # bogus "project:None" tag when no project is configured.
    config = Config({'url': 'http://localhost:8081', 'tags': []})
    assert config.tags == []


# ---------------------------------------------------------------------------
# TwistlockCheck.__init__
# ---------------------------------------------------------------------------


def test_init_builds_config_from_first_instance(instance):
    # Kills the core/ReplaceUnaryOperator_Delete_Not and core/AddNot mutants at twistlock.py:45
    # (`if instances:` flipped would skip building `_config` even though an instance was given), and the
    # core/NumberReplacer mutant at twistlock.py:46 (`instances[0]` -> `instances[-1]`).
    other_instance = dict(instance, url='http://otherhost:9999')
    check = TwistlockCheck('twistlock', {}, [instance, other_instance])
    assert check._config is not None
    assert check._config.url == instance['url']


def test_init_without_instances_leaves_config_unset():
    # Kills the core/ReplaceUnaryOperator_Delete_Not and core/AddNot mutants at twistlock.py:45
    # (with no instances, `_config` must stay None, not get built from a missing instance).
    check = TwistlockCheck('twistlock', {}, [])
    assert check._config is None


# ---------------------------------------------------------------------------
# TwistlockCheck.check
# ---------------------------------------------------------------------------


def test_check_builds_config_lazily_when_missing(instance):
    # Kills the core/ReplaceUnaryOperator_Delete_Not and core/AddNot mutants at twistlock.py:52
    # (`if not self._config:` flipped would skip building `_config` for a check created with no instances).
    check = TwistlockCheck('twistlock', {}, [])
    assert check._config is None
    with pytest.raises(Exception):
        check.check(instance)
    assert check._config is not None
    assert check._config.username == instance['username']


def test_check_requires_username_and_password():
    # Kills the core/ReplaceOrWithAnd mutant at twistlock.py:55 (`or` flipped to `and` would only
    # raise when BOTH username and password are missing, instead of when either one is missing).
    check = TwistlockCheck('twistlock', {}, [])
    with pytest.raises(Exception, match='requires both a username and a password'):
        check.check({'url': 'http://localhost:8081', 'username': 'admin'})


def test_check_computes_warning_and_critical_dates_from_current_date(instance):
    # Kills the core/ReplaceBinaryOperator_Sub_Add and core/NumberReplacer mutants at twistlock.py:61-62
    # (the 7-hour warning offset and 1-day critical offset subtracted from `current_date`).
    check = TwistlockCheck('twistlock', {}, [instance])
    with mock.patch('requests.Session.get', return_value=MockResponse('{}'), autospec=True):
        with pytest.raises(Exception):
            check.check(instance)

    assert check.warning_date == check.current_date - timedelta(hours=7)
    assert check.critical_date == check.current_date - timedelta(days=1)
    assert check.warning_date > check.critical_date


# ---------------------------------------------------------------------------
# TwistlockCheck.report_license_expiration
# ---------------------------------------------------------------------------


def license_response(expiration_date):
    return MockResponse(json_data={'expiration_date': expiration_date.isoformat()})


@pytest.mark.parametrize(
    'expires_in_days, expected_status',
    [
        (29, AgentCheck.WARNING),  # inside the 30d warning window, outside the 7d critical window
        (30, AgentCheck.OK),  # exactly on the 30d warning boundary -> not yet in the window
        (31, AgentCheck.OK),  # outside the 30d warning window
        (7, AgentCheck.WARNING),  # exactly on the 7d critical boundary -> warning, not critical
        (6.5, AgentCheck.CRITICAL),  # inside the 7d critical window
        (7.5, AgentCheck.WARNING),  # inside the 30d warning window but outside the 7d critical window
    ],
)
def test_report_license_expiration_status_boundaries(aggregator, instance, expires_in_days, expected_status):
    # Kills the core/ReplaceBinaryOperator_Add_Sub, core/NumberReplacer, core/ReplaceComparisonOperator_Lt_*,
    # and core/AddNot mutants at twistlock.py:88, :89, :92, and :94 by pinning the license expiration_date
    # exactly on/around the 30-day warning and 7-day critical thresholds relative to a frozen "now".
    check = TwistlockCheck('twistlock', {}, [instance])
    expiration = FrozenDateTime.FIXED_NOW + timedelta(days=expires_in_days)

    with mock.patch('datadog_checks.twistlock.twistlock.datetime', FrozenDateTime):
        with mock.patch('requests.Session.get', return_value=license_response(expiration), autospec=True):
            check.report_license_expiration()

    aggregator.assert_service_check('twistlock.license_ok', expected_status)


def test_report_license_expiration_message_set_only_when_not_ok(aggregator, instance):
    # Kills the core/ReplaceComparisonOperator_IsNot_Lt mutant at twistlock.py:97 (`is not AgentCheck.OK`
    # flipped to `< AgentCheck.OK` would never be true, since no status is below AgentCheck.OK).
    check = TwistlockCheck('twistlock', {}, [instance])
    expiration = FrozenDateTime.FIXED_NOW + timedelta(days=1)

    with mock.patch('datadog_checks.twistlock.twistlock.datetime', FrozenDateTime):
        with mock.patch('requests.Session.get', return_value=license_response(expiration), autospec=True):
            check.report_license_expiration()

    service_check = aggregator.service_checks('twistlock.license_ok')[0]
    assert service_check.message == expiration.isoformat()


def test_report_license_expiration_retrieval_failure_raises_and_reports_critical(aggregator, instance):
    check = TwistlockCheck('twistlock', {}, [instance])
    with mock.patch('requests.Session.get', return_value=MockResponse('{}'), autospec=True):
        with pytest.raises(Exception, match='expiration_date not found'):
            check.report_license_expiration()

    aggregator.assert_service_check('twistlock.license_ok', AgentCheck.CRITICAL)


# ---------------------------------------------------------------------------
# TwistlockCheck._report_service_check
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'scan_day, expected_status',
    [
        (11, AgentCheck.OK),  # outside the warning window entirely
        (9, AgentCheck.WARNING),  # just inside the warning window
        (10, AgentCheck.OK),  # exactly on the warning boundary -> not yet in the window
        (5, AgentCheck.WARNING),  # exactly on the critical boundary -> warning, not critical
        (4, AgentCheck.CRITICAL),  # just inside the critical window
        (6, AgentCheck.WARNING),  # inside the warning window but outside the critical window
    ],
)
def test_report_service_check_status_boundaries(aggregator, instance, scan_day, expected_status):
    # Kills the core/ReplaceComparisonOperator_Lt_* and core/AddNot mutants at twistlock.py:311 and :313
    # by pinning scan_date exactly on/around the warning_date and critical_date thresholds.
    check = TwistlockCheck('twistlock', {}, [instance])
    check.warning_date = datetime(2024, 1, 10, tzinfo=timezone.utc)
    check.critical_date = datetime(2024, 1, 5, tzinfo=timezone.utc)
    scan_date = datetime(2024, 1, scan_day, tzinfo=timezone.utc)

    check._report_service_check({'scanTime': scan_date.isoformat()}, 'twistlock.registry')

    aggregator.assert_service_check('twistlock.registry.is_scanned', expected_status)


# ---------------------------------------------------------------------------
# TwistlockCheck._analyze_vulnerability
# ---------------------------------------------------------------------------


def test_analyze_vulnerability_default_flags_report_systems_type(aggregator, instance):
    # Kills the core/ReplaceFalseWithTrue mutants at twistlock.py:232 (the `host=False, image=False`
    # defaults); either flipping to True would misclassify a plain call as a host or image CVE.
    check = TwistlockCheck('twistlock', {}, [instance])
    check.last_run = datetime(2024, 1, 10)
    check._analyze_vulnerability(make_vuln('CVE-DEFAULT', datetime(2024, 1, 9)))

    assert 'affecting your systems' in aggregator.events[0]['msg_text']


def test_analyze_vulnerability_host_flag_reports_hosts_type(aggregator, instance):
    # Kills the core/AddNot mutant at twistlock.py:245 (`if host:` flipped to `if not host:`
    # would report a host CVE under the generic "systems" message instead of "hosts").
    check = TwistlockCheck('twistlock', {}, [instance])
    check.last_run = datetime(2024, 1, 10)
    check._analyze_vulnerability(make_vuln('CVE-HOST', datetime(2024, 1, 9)), host=True)

    assert 'affecting your hosts' in aggregator.events[0]['msg_text']


def test_analyze_vulnerability_without_cve_id_is_ignored(aggregator, instance):
    # Kills the core/ReplaceUnaryOperator_Delete_Not and core/AddNot mutants at twistlock.py:235
    # (`if not cve_id:` flipped would try to process a record that has no CVE id).
    check = TwistlockCheck('twistlock', {}, [instance])
    check.last_run = datetime(2024, 1, 10)
    check._analyze_vulnerability({'description': 'no id here', 'published': 0})

    assert aggregator.events == []


@pytest.mark.parametrize(
    'published_day, expect_event',
    [
        (9, True),  # published strictly before last_run -> new CVE, event fires
        (10, False),  # published exactly at last_run -> not "new" (strict less-than)
        (11, False),  # published after last_run -> not new
    ],
)
def test_analyze_vulnerability_only_fires_for_cves_published_before_last_run(
    aggregator, instance, published_day, expect_event
):
    # Kills the core/ReplaceComparisonOperator_Lt_* and core/AddNot mutants at twistlock.py:244
    # by pinning `published` exactly on/around `self.last_run`. Both sides are naive datetimes here
    # (matching the check's own `datetime.fromtimestamp` without a timezone) so the comparison is valid.
    check = TwistlockCheck('twistlock', {}, [instance])
    check.last_run = datetime(2024, 1, 10)
    check._analyze_vulnerability(make_vuln('CVE-BOUNDARY', datetime(2024, 1, published_day)))

    assert bool(aggregator.events) is expect_event


# ---------------------------------------------------------------------------
# TwistlockCheck.report_vulnerabilities
# ---------------------------------------------------------------------------


def test_report_vulnerabilities_routes_host_and_image_vulns(aggregator, instance):
    # Kills the core/ZeroIterationForLoop, core/ReplaceUnaryOperator_Delete_Not (x2), core/AddNot,
    # core/ReplaceAndWithOr, core/ReplaceContinueWithBreak, and core/ReplaceTrueWithFalse mutants
    # across twistlock.py:219-230 (vulnerability-container iteration and host/image routing).
    check = TwistlockCheck('twistlock', {}, [instance])
    check.last_run = datetime(2030, 1, 1)
    published = datetime(2020, 1, 1)

    containers = [
        {},  # neither host nor image vulns -> must be skipped without stopping the loop
        {
            'hostVulnerabilities': [make_vuln('CVE-HOST', published)],
            'imageVulnerabilities': [make_vuln('CVE-IMAGE', published)],
        },
        {'hostVulnerabilities': [make_vuln('CVE-HOST-ONLY', published)]},
        {'imageVulnerabilities': [make_vuln('CVE-IMAGE-ONLY', published)]},
    ]
    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=containers), autospec=True):
        check.report_vulnerabilities()

    events_by_title = {event['msg_title']: event for event in aggregator.events}
    assert set(events_by_title) == {'CVE-HOST', 'CVE-IMAGE', 'CVE-HOST-ONLY', 'CVE-IMAGE-ONLY'}
    assert 'affecting your hosts' in events_by_title['CVE-HOST']['msg_text']
    assert 'affecting your images' in events_by_title['CVE-IMAGE']['msg_text']


# ---------------------------------------------------------------------------
# TwistlockCheck._report_vuln_info
# ---------------------------------------------------------------------------


def test_report_vuln_info_counts_and_gauges_by_severity(aggregator, instance):
    # Kills the core/ZeroIterationForLoop, core/NumberReplacer (x6), and core/AddNot mutants at
    # twistlock.py:272, :274, :278, :280, and :282.
    check = TwistlockCheck('twistlock', {}, [instance])
    data = {
        'vulnerabilities': [
            {'cve': 'CVE-1', 'severity': 'high', 'packageName': 'pkg-a'},
            {'cve': 'CVE-2', 'severity': 'high'},
        ]
    }
    check._report_vuln_info('twistlock.registry', data, [])

    high_counts = [m for m in aggregator.metrics('twistlock.registry.cve.count') if 'severity:high' in m.tags]
    assert len(high_counts) == 1
    assert high_counts[0].value == 2

    low_counts = [m for m in aggregator.metrics('twistlock.registry.cve.count') if 'severity:low' in m.tags]
    assert len(low_counts) == 1
    assert low_counts[0].value == 0

    detail_metrics = aggregator.metrics('twistlock.registry.cve.details')
    assert len(detail_metrics) == 2
    assert all(m.value == 1 for m in detail_metrics)
    assert any('package:pkg-a' in m.tags for m in detail_metrics)


# ---------------------------------------------------------------------------
# TwistlockCheck._report_compliance_information
# ---------------------------------------------------------------------------


def test_report_compliance_information_sums_by_severity(aggregator, instance):
    # Kills the core/ReplaceOrWithAnd mutant at twistlock.py:290 and the core/NumberReplacer
    # mutants at twistlock.py:293.
    check = TwistlockCheck('twistlock', {}, [instance])
    data = {'complianceDistribution': {'high': 3}}
    check._report_compliance_information('twistlock.registry', data, [])

    high = [m for m in aggregator.metrics('twistlock.registry.compliance.count') if 'severity:high' in m.tags][0]
    assert high.value == 3

    low = [m for m in aggregator.metrics('twistlock.registry.compliance.count') if 'severity:low' in m.tags][0]
    assert low.value == 0


# ---------------------------------------------------------------------------
# TwistlockCheck._report_layer_count
# ---------------------------------------------------------------------------


def test_report_layer_count_sums_sizes_and_counts_layers(aggregator, instance):
    # Kills the core/NumberReplacer and core/ZeroIterationForLoop mutants across twistlock.py:299-303
    # (layer_count/layer_sizes initialization, loop iteration, and per-layer accumulation).
    check = TwistlockCheck('twistlock', {}, [instance])
    data = {'history': [{'sizeBytes': 100}, {}]}
    check._report_layer_count(data, 'twistlock.registry', [])

    assert aggregator.metrics('twistlock.registry.size')[0].value == 100
    assert aggregator.metrics('twistlock.registry.layer_count')[0].value == 2


# ---------------------------------------------------------------------------
# TwistlockCheck.report_registry_scan
# ---------------------------------------------------------------------------


def test_report_registry_scan_retrieval_failure_reports_critical(aggregator, instance):
    # Kills the core/ExceptionReplacer mutant at twistlock.py:106.
    check = TwistlockCheck('twistlock', {}, [instance])
    with mock.patch('requests.Session.get', side_effect=Exception('boom'), autospec=True):
        check.report_registry_scan()

    aggregator.assert_service_check('twistlock.can_connect', AgentCheck.CRITICAL)


def test_report_registry_scan_skips_invalid_entries_and_strips_dockerio_prefix(aggregator, instance):
    # Kills the core/ReplaceContinueWithBreak mutant at twistlock.py:113 and the core/AddNot
    # mutant at twistlock.py:116.
    check = TwistlockCheck('twistlock', {}, [instance])
    check.warning_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    check.critical_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    scan_result = [
        {'no_id_here': True},
        {'_id': 'docker.io/myimage', 'history': [], 'scanTime': '2019-01-01T00:00:00Z'},
    ]
    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=scan_result), autospec=True):
        check.report_registry_scan()

    tags = set()
    for m in aggregator.metrics('twistlock.registry.layer_count'):
        tags.update(m.tags)
    assert 'scanned_image:myimage' in tags


# ---------------------------------------------------------------------------
# TwistlockCheck.report_images_scan
# ---------------------------------------------------------------------------


def test_report_images_scan_retrieval_failure_reports_critical(aggregator, instance):
    # Kills the core/ExceptionReplacer mutant at twistlock.py:133.
    check = TwistlockCheck('twistlock', {}, [instance])
    with mock.patch('requests.Session.get', side_effect=Exception('boom'), autospec=True):
        check.report_images_scan()

    aggregator.assert_service_check('twistlock.can_connect', AgentCheck.CRITICAL)


def test_report_images_scan_skips_invalid_entries_and_picks_first_instance(aggregator, instance):
    # Kills the core/ReplaceContinueWithBreak mutants at twistlock.py:141, :145, and :149, the
    # core/NumberReplacer mutant at twistlock.py:146 (`instances[0]` -> `instances[-1]`), and the
    # core/AddNot mutant at twistlock.py:150.
    check = TwistlockCheck('twistlock', {}, [instance])
    check.warning_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    check.critical_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    scan_result = [
        {'no_id_here': True},
        {'_id': 'no-instances', 'instances': []},
        {'_id': 'no-image-name', 'instances': [{}]},
        {
            '_id': 'valid',
            'instances': [{'image': 'docker.io/first-image'}, {'image': 'docker.io/second-image'}],
            'history': [],
            'scanTime': '2019-01-01T00:00:00Z',
        },
    ]
    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=scan_result), autospec=True):
        check.report_images_scan()

    tags = set()
    for m in aggregator.metrics('twistlock.images.layer_count'):
        tags.update(m.tags)
    assert 'scanned_image:first-image' in tags


# ---------------------------------------------------------------------------
# TwistlockCheck.report_hosts_scan
# ---------------------------------------------------------------------------


def test_report_hosts_scan_retrieval_failure_reports_critical(aggregator, instance):
    # Kills the core/ExceptionReplacer mutant at twistlock.py:167.
    check = TwistlockCheck('twistlock', {}, [instance])
    with mock.patch('requests.Session.get', side_effect=Exception('boom'), autospec=True):
        check.report_hosts_scan()

    aggregator.assert_service_check('twistlock.can_connect', AgentCheck.CRITICAL)


def test_report_hosts_scan_skips_hosts_without_hostname(aggregator, instance):
    # Kills the core/ReplaceContinueWithBreak mutant at twistlock.py:175.
    check = TwistlockCheck('twistlock', {}, [instance])
    check.warning_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    check.critical_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    scan_result = [
        {'no_hostname_here': True},
        {'hostname': 'host-1', 'scanTime': '2019-01-01T00:00:00Z'},
    ]
    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=scan_result), autospec=True):
        check.report_hosts_scan()

    tags = set()
    for service_check in aggregator.service_checks('twistlock.hosts.is_scanned'):
        tags.update(service_check.tags)
    assert 'scanned_host:host-1' in tags


# ---------------------------------------------------------------------------
# TwistlockCheck.report_container_compliance
# ---------------------------------------------------------------------------


def test_report_container_compliance_retrieval_failure_reports_critical(aggregator, instance):
    # Kills the core/ExceptionReplacer mutant at twistlock.py:192.
    check = TwistlockCheck('twistlock', {}, [instance])
    with mock.patch('requests.Session.get', side_effect=Exception('boom'), autospec=True):
        check.report_container_compliance()

    aggregator.assert_service_check('twistlock.can_connect', AgentCheck.CRITICAL)


def test_report_container_compliance_tags_and_skips_invalid_entries(aggregator, instance):
    # Kills the core/ReplaceContinueWithBreak mutant at twistlock.py:200 and the core/AddNot
    # mutants at twistlock.py:204 and :207.
    check = TwistlockCheck('twistlock', {}, [instance])
    check.warning_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    check.critical_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    scan_result = [
        {'no_id_here': True},
        {'_id': 'c1', 'name': 'my-container', 'imageName': 'my-image', 'scanTime': '2019-01-01T00:00:00Z'},
    ]
    with mock.patch('requests.Session.get', return_value=MockResponse(json_data=scan_result), autospec=True):
        check.report_container_compliance()

    tags = set()
    for service_check in aggregator.service_checks('twistlock.containers.is_scanned'):
        tags.update(service_check.tags)
    assert 'container_name:my-container' in tags
    assert 'image_name:my-image' in tags


# ---------------------------------------------------------------------------
# TwistlockCheck._retrieve_json
# ---------------------------------------------------------------------------


def test_retrieve_json_includes_project_query_param_when_configured(instance):
    # Kills the core/AddNot mutant at twistlock.py:320 (`if project else None` -> `if not project else None`).
    instance['project'] = 'my-project'
    check = TwistlockCheck('twistlock', {}, [instance])

    with mock.patch('requests.Session.get', return_value=MockResponse('{}'), autospec=True) as get:
        check._retrieve_json('/api/v1/registry')

    assert get.call_args.kwargs['params'] == {'project': 'my-project'}


def test_retrieve_json_logs_and_reraises_on_parse_failure(instance, caplog):
    # Kills the core/ExceptionReplacer mutant at twistlock.py:332 (`except Exception` -> `except
    # CosmicRayTestingException`), observable via the debug log emitted before the exception is re-raised.
    check = TwistlockCheck('twistlock', {}, [instance])

    with mock.patch('requests.Session.get', return_value=MockResponse('not valid json'), autospec=True):
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(Exception):
                check._retrieve_json('/api/v1/registry')

    assert any('cannot get a response' in message for message in caplog.messages)
