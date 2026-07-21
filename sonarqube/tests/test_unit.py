# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os

import mock
import pytest
import requests

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.http import MockResponse
from datadog_checks.sonarqube.constants import MAX_PAGES

from .common import HERE
from .metrics import WEB_METRICS

pytestmark = [pytest.mark.unit]


def test_service_check_critical(aggregator, dd_run_check, sonarqube_check, web_instance):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = requests.exceptions.RequestException('Req Exception')
        check = sonarqube_check(web_instance)
        global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
        global_tags.extend(web_instance['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            assert len(aggregator.metrics(metric_name)) == 0
        aggregator.assert_service_check('sonarqube.api_access', status=check.CRITICAL, tags=global_tags)


def test_service_check_ok_version_empty(aggregator, dd_run_check, sonarqube_check, web_instance):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version_empty')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance)
        global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
        global_tags.extend(web_instance['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok(aggregator, dd_run_check, sonarqube_check, web_instance):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance)
        global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
        global_tags.extend(web_instance['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_config_none(aggregator, dd_run_check, sonarqube_check, web_instance_config_none):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_config_none)
        global_tags = ['endpoint:{}'.format(web_instance_config_none['web_endpoint'])]
        global_tags.extend(web_instance_config_none['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_and_exclude_metrics(
    aggregator, dd_run_check, sonarqube_check, web_instance_and_exclude_metrics
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_and_exclude_metrics)
        global_tags = ['endpoint:{}'.format(web_instance_and_exclude_metrics['web_endpoint'])]
        global_tags.extend(web_instance_and_exclude_metrics['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_only_include)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_only_include['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_only_include_metrics_empty(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_empty')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component_empty')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_only_include)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_only_include['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            assert len(aggregator.metrics(metric_name)) == 0
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_exclude(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_include_all_and_exclude
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp_p1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp_p2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_exclude)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_include_all_and_exclude['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_include_all_and_exclude['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            expect_count = 2 if metric_name == 'sonarqube.issues.new_blocker_violations' else 1
            aggregator.assert_metric(
                metric_name, count=expect_count, tags=global_tags + ['project:org.sonarqube:sonarqube-scanner']
            )
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_include_all_and_limit(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_include_all_and_limit
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp_p1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search_with_tmp_p2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_include_all_and_limit)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_include_all_and_limit['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_include_all_and_limit['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            expect_count = 2 if metric_name == 'sonarqube.issues.new_blocker_violations' else 1
            aggregator.assert_metric(metric_name, count=expect_count, tags=global_tags + ['project:tmp_project'])
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_component_and_autodiscovery(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_component_and_autodiscovery
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_component_and_autodiscovery)
        global_tags = ['endpoint:{}'.format(web_instance_with_component_and_autodiscovery['web_endpoint'])]
        global_tags.extend(web_instance_with_component_and_autodiscovery['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            expect_count = 2 if metric_name == 'sonarqube.issues.new_blocker_violations' else 1
            aggregator.assert_metric(metric_name, count=expect_count)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_service_check_ok_with_autodiscovery_config_none(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_config_none
):
    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'version')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_1')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'metrics_search_p_2')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'components_search')),
            MockResponse(file_path=os.path.join(HERE, 'api_responses', 'measures_component')),
        ]
        check = sonarqube_check(web_instance_with_autodiscovery_config_none)
        global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_config_none['web_endpoint'])]
        global_tags.extend(web_instance_with_autodiscovery_config_none['tags'])
        dd_run_check(check)
        for metric_name in WEB_METRICS:
            aggregator.assert_metric(metric_name)
        aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_default_components_discovery_limit_is_ten(sonarqube_check, web_instance):
    # Kills the core/NumberReplacer mutants at check.py:16 (_DEFAULT_COMPONENTS_DISCOVERY_LIMIT 10 -> 11/9).
    check = sonarqube_check(web_instance)

    assert check._DEFAULT_COMPONENTS_DISCOVERY_LIMIT == 10


def test_max_pages_constant():
    # Kills the core/NumberReplacer mutants at constants.py:8 (MAX_PAGES 100 -> 101/99).
    assert MAX_PAGES == 100


def test_collect_metadata_skips_when_collection_disabled(datadog_agent, sonarqube_check):
    # Kills the core/RemoveDecorator mutant at check.py:40 (removes @AgentCheck.metadata_entrypoint).
    datadog_agent._config['enable_metadata_collection'] = False
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        check.collect_metadata()
        datadog_agent.reset()
        mock_http.get.assert_not_called()


def test_collect_components_discovery_skips_known_component_but_processes_next(aggregator, sonarqube_check):
    # Kills the core/ReplaceContinueWithBreak mutant at check.py:72 (`continue` -> `break` for known components).
    instance = {
        'web_endpoint': 'http://sonarqube.example',
        'components': {'known': {'tag': 'project'}},
        'components_discovery': {'include': {'.*': {'tag': 'project'}}},
    }
    check = sonarqube_check(instance)
    check.parse_config()
    available_metrics = {'ncloc': 'size.ncloc'}

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(json_data={'paging': {'total': 2}, 'components': [{'key': 'known'}, {'key': 'discovered'}]}),
            MockResponse(json_data={'component': {'measures': [{'metric': 'ncloc', 'value': '1'}]}}),
        ]
        check.collect_components_discovery(available_metrics)

    aggregator.assert_metric(
        'sonarqube.size.ncloc', tags=['project:discovered', 'endpoint:http://sonarqube.example'], count=1
    )


def test_collect_components_discovery_logs_singular_component_count(caplog, sonarqube_check):
    # Kills core/ReplaceComparisonOperator_Eq_{NotEq,Lt,Gt}, AddNot and NumberReplacer(==2/==0) at check.py:78.
    instance = {
        'web_endpoint': 'http://sonarqube.example',
        'components_discovery': {'include': {'.*': {'tag': 'project'}}},
    }
    check = sonarqube_check(instance)
    check.parse_config()

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http, caplog.at_level(logging.DEBUG):
        mock_http.get.side_effect = [
            MockResponse(json_data={'paging': {'total': 1}, 'components': [{'key': 'only'}]}),
            MockResponse(json_data={'component': {'measures': []}}),
        ]
        check.collect_components_discovery({})

    assert 'collected 1 component' in caplog.text
    assert 'collected 1 components' not in caplog.text


def test_collect_components_discovery_logs_plural_component_count(caplog, sonarqube_check):
    # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at check.py:78 (`== 1` -> `>= 1`).
    instance = {
        'web_endpoint': 'http://sonarqube.example',
        'components_discovery': {'include': {'.*': {'tag': 'project'}}},
    }
    check = sonarqube_check(instance)
    check.parse_config()

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http, caplog.at_level(logging.DEBUG):
        mock_http.get.side_effect = [
            MockResponse(json_data={'paging': {'total': 2}, 'components': [{'key': 'c1'}, {'key': 'c2'}]}),
            MockResponse(json_data={'component': {'measures': []}}),
            MockResponse(json_data={'component': {'measures': []}}),
        ]
        check.collect_components_discovery({})

    assert 'collected 2 components' in caplog.text


def test_collect_components_discovery_stops_exactly_at_limit(aggregator, sonarqube_check):
    # Kills the core/ReplaceComparisonOperator_Eq_LtE mutant at check.py:80 (`== discovery_limit` -> `<=`).
    instance = {
        'web_endpoint': 'http://sonarqube.example',
        'components_discovery': {'limit': 2, 'include': {'.*': {'tag': 'project'}}},
    }
    check = sonarqube_check(instance)
    check.parse_config()
    available_metrics = {'ncloc': 'size.ncloc'}

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(
                json_data={'paging': {'total': 3}, 'components': [{'key': 'c1'}, {'key': 'c2'}, {'key': 'c3'}]}
            ),
            MockResponse(json_data={'component': {'measures': [{'metric': 'ncloc', 'value': '1'}]}}),
            MockResponse(json_data={'component': {'measures': [{'metric': 'ncloc', 'value': '1'}]}}),
        ]
        check.collect_components_discovery(available_metrics)

    aggregator.assert_metric('sonarqube.size.ncloc', count=2)


def test_collect_components_discovery_zero_limit_never_stops_early(aggregator, sonarqube_check):
    # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at check.py:80 (`== discovery_limit` -> `>=`).
    instance = {
        'web_endpoint': 'http://sonarqube.example',
        'components_discovery': {'limit': 0, 'include': {'.*': {'tag': 'project'}}},
    }
    check = sonarqube_check(instance)
    check.parse_config()
    available_metrics = {'ncloc': 'size.ncloc'}

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(json_data={'paging': {'total': 2}, 'components': [{'key': 'c1'}, {'key': 'c2'}]}),
            MockResponse(json_data={'component': {'measures': [{'metric': 'ncloc', 'value': '1'}]}}),
            MockResponse(json_data={'component': {'measures': [{'metric': 'ncloc', 'value': '1'}]}}),
        ]
        check.collect_components_discovery(available_metrics)

    aggregator.assert_metric('sonarqube.size.ncloc', count=2)


def test_collect_metrics_from_component_only_queries_selected_metrics(sonarqube_check):
    # Kills core/ZeroIterationForLoop at check.py:92 and core/AddNot at check.py:93 (should_collect_metric filter).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})
    available_metrics = {'ncloc': 'size.ncloc', 'bugs': 'reliability.bugs'}

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.return_value = MockResponse(json_data={'component': {'measures': []}})
        check.collect_metrics_from_component(
            available_metrics, 'proj', 'project', lambda metric: metric == 'size.ncloc'
        )

    assert mock_http.get.call_args[1]['params']['metricKeys'] == 'ncloc'


def test_collect_metrics_from_component_warns_when_no_metrics_match(caplog, sonarqube_check):
    # Kills core/ReplaceUnaryOperator_Delete_Not and core/AddNot at check.py:95 (`if not keys_to_query`).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})
    available_metrics = {'ncloc': 'size.ncloc'}

    with (
        mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http,
        caplog.at_level(logging.WARNING),
    ):
        mock_http.get.return_value = MockResponse(json_data={'component': {'measures': []}})
        check.collect_metrics_from_component(available_metrics, 'proj', 'project', lambda metric: False)

    assert 'does not match any available metrics' in caplog.text


def test_discover_available_metrics_paginates_from_page_one(sonarqube_check):
    # Kills core/NumberReplacer at check.py:117 (page = 1 -> 2/0) and check.py:137 (page += 1 -> += 2/0).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(
                json_data={'total': 2, 'metrics': [{'key': 'm1', 'domain': 'Size', 'type': 'INT', 'hidden': False}]}
            ),
            MockResponse(
                json_data={'total': 2, 'metrics': [{'key': 'm2', 'domain': 'Size', 'type': 'INT', 'hidden': False}]}
            ),
        ]
        available_metrics = check.discover_available_metrics()

    assert [call[1]['params']['p'] for call in mock_http.get.call_args_list] == [1, 2]
    assert available_metrics == {'m1': 'size.m1', 'm2': 'size.m2'}


def test_discover_available_metrics_skips_unknown_category_and_continues(sonarqube_check):
    # Kills the core/ReplaceContinueWithBreak mutant at check.py:135 (unknown category `continue` -> `break`).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(
                json_data={
                    'total': 2,
                    'metrics': [
                        {'key': 'unknown_metric', 'domain': 'NotACategory', 'type': 'INT', 'hidden': False},
                        {'key': 'known_metric', 'domain': 'Size', 'type': 'INT', 'hidden': False},
                    ],
                }
            ),
        ]
        available_metrics = check.discover_available_metrics()

    assert available_metrics == {'known_metric': 'size.known_metric'}


def test_discover_available_components_paginates_from_page_one(sonarqube_check):
    # Kills core/NumberReplacer at check.py:142 (page = 1 -> 2/0) and check.py:156 (page += 1 -> += 2/0).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    with mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http:
        mock_http.get.side_effect = [
            MockResponse(json_data={'paging': {'total': 2}, 'components': [{'key': 'c1'}]}),
            MockResponse(json_data={'paging': {'total': 2}, 'components': [{'key': 'c2'}]}),
        ]
        available_components = check.discover_available_components()

    assert [call[1]['params']['p'] for call in mock_http.get.call_args_list] == [1, 2]
    assert available_components == ['c1', 'c2']


def test_collect_version_warns_when_version_is_empty(caplog, sonarqube_check):
    # Kills core/ReplaceUnaryOperator_Delete_Not and core/AddNot at check.py:164 (`if not version`).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    with (
        mock.patch('datadog_checks.sonarqube.check.SonarqubeCheck.http') as mock_http,
        caplog.at_level(logging.WARNING),
    ):
        mock_http.get.return_value = MockResponse(content='')
        check.collect_version()

    assert 'The SonarQube version was not found in response' in caplog.text


def test_component_include_pattern_overrides_default(sonarqube_check):
    # Kills the core/ReplaceOrWithAnd mutant at check.py:196 (include-pattern `or` default_include -> `and`).
    check = sonarqube_check({'components': {'foo': {'include': ['bar.']}}, 'default_include': ['foo.']})
    check.parse_config()
    _, selector = check._components['foo']

    assert selector('bar.baz')
    assert not selector('foo.bar')


def test_component_matchers_default_to_include_all_exclude_none(sonarqube_check):
    # Kills core/ReplaceTrueWithFalse at check.py:197 and core/ReplaceFalseWithTrue at check.py:201.
    check = sonarqube_check({'components': {'foo': {}}})
    check.parse_config()
    _, selector = check._components['foo']

    assert selector('anything.at.all')


def test_component_exclude_pattern_overrides_default(sonarqube_check):
    # Kills the core/ReplaceOrWithAnd mutant at check.py:200 (exclude-pattern `or` default_exclude -> `and`).
    check = sonarqube_check(
        {'components': {'foo': {'include': ['foo.'], 'exclude': ['foo.baz']}}, 'default_exclude': ['foo.qux']}
    )
    check.parse_config()
    _, selector = check._components['foo']

    assert selector('foo.bar')
    assert not selector('foo.baz')


def test_component_selector_excludes_matching_metrics(sonarqube_check):
    # Kills core/ReplaceUnaryOperator_Delete_Not and core/ReplaceAndWithOr at check.py:209 (selector combinator).
    check = sonarqube_check({'components': {'foo': {'exclude': ['foo.']}}})
    check.parse_config()
    _, selector = check._components['foo']

    assert not selector('foo.bar')
    assert selector('bar.baz')


def test_discovery_include_metric_pattern_overrides_default(sonarqube_check):
    # Kills the core/ReplaceOrWithAnd mutant at check.py:231 (include-pattern `or` default_include -> `and`).
    check = sonarqube_check(
        {'components_discovery': {'include': {'.*': {'include': ['bar.']}}}, 'default_include': ['foo.']}
    )
    check.parse_config()
    _, discovery_data = check._components_discovery
    _, _, should_collect_metric = discovery_data['.*']

    assert should_collect_metric('bar.baz')
    assert not should_collect_metric('foo.bar')


def test_discovery_metric_matchers_default_to_include_all_exclude_none(sonarqube_check):
    # Kills core/ReplaceTrueWithFalse at check.py:232 and core/ReplaceFalseWithTrue at check.py:236.
    check = sonarqube_check({'components_discovery': {'include': {'.*': {}}}})
    check.parse_config()
    _, discovery_data = check._components_discovery
    _, _, should_collect_metric = discovery_data['.*']

    assert should_collect_metric('anything.at.all')


def test_discovery_exclude_metric_pattern_overrides_default(sonarqube_check):
    # Kills the core/ReplaceOrWithAnd mutant at check.py:235 (exclude-pattern `or` default_exclude -> `and`).
    check = sonarqube_check(
        {'components_discovery': {'include': {'.*': {'exclude': ['foo.baz']}}}, 'default_exclude': ['foo.qux']}
    )
    check.parse_config()
    _, discovery_data = check._components_discovery
    _, _, should_collect_metric = discovery_data['.*']

    assert not should_collect_metric('foo.baz')
    assert should_collect_metric('foo.qux')


def test_discovery_selector_excludes_matching_metrics(sonarqube_check):
    # Kills core/ReplaceUnaryOperator_Delete_Not and core/ReplaceAndWithOr at check.py:246 (metric combinator).
    check = sonarqube_check({'components_discovery': {'include': {'.*': {'exclude': ['foo.']}}}})
    check.parse_config()
    _, discovery_data = check._components_discovery
    _, _, should_collect_metric = discovery_data['.*']

    assert not should_collect_metric('foo.bar')
    assert should_collect_metric('bar.baz')


def test_compile_metric_patterns_returns_compiled_pattern_for_valid_input(sonarqube_check):
    # Kills core/ZeroIterationForLoop and core/NumberReplacer at check.py:260 (enumerate start).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    pattern = check.compile_metric_patterns({'include': ['bar.']}, 'include')

    assert pattern is not None
    assert pattern.match('bar.baz')


def test_compile_metric_patterns_returns_none_when_field_absent(sonarqube_check):
    # Kills the core/AddNot mutant at check.py:280 (`if patterns else None` -> `if not patterns else None`).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    assert check.compile_metric_patterns({}, 'include') is None


def test_compile_metric_patterns_error_message_uses_one_based_index(sonarqube_check):
    # Kills the core/NumberReplacer mutants at check.py:260 (enumerate(metric_patterns, 1) -> start at 2/0).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    with pytest.raises(ConfigurationError, match=r'Pattern #2 in `include` setting must be a string'):
        check.compile_metric_patterns({'include': ['valid.', 9000]}, 'include')


def test_compile_component_patterns_error_message_uses_one_based_index(sonarqube_check):
    # Kills the core/NumberReplacer mutants at check.py:288 (enumerate(component_patterns, 1) -> start at 2/0).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    with pytest.raises(ConfigurationError, match=r'Pattern #2 in `exclude` setting must be a string'):
        check.compile_component_patterns({'exclude': ['valid_prefix', 9000]}, 'exclude')


def test_is_valid_metric_requires_visible_and_numeric_type(sonarqube_check):
    # Kills the core/ReplaceAndWithOr mutant at check.py:316 (`not hidden and numeric_type` -> `or`).
    check = sonarqube_check({'web_endpoint': 'http://sonarqube.example'})

    assert not check.is_valid_metric({'hidden': True, 'type': 'INT'})
    assert not check.is_valid_metric({'hidden': False, 'type': 'STRING'})
    assert check.is_valid_metric({'hidden': False, 'type': 'INT'})
