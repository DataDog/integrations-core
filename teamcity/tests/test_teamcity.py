# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest
from mock import ANY, MagicMock, patch

from datadog_checks.teamcity import TeamCityCheck

from .common import CHECK_NAME, CONFIG, HERE, REST_METRICS


@pytest.mark.integration
def test_build_event(aggregator):
    teamcity = TeamCityCheck(CHECK_NAME, {}, [CONFIG])

    with patch('datadog_checks.base.utils.http.requests.get', get_mock_first_build):
        teamcity.check(CONFIG['instances'][0])

    assert len(aggregator.metric_names) == 0
    assert len(aggregator.events) == 0
    aggregator.reset()

    with patch('datadog_checks.base.utils.http.requests.get', get_mock_one_more_build):
        teamcity.check(CONFIG['instances'][0])

    events = aggregator.events
    assert len(events) == 1
    assert events[0]['msg_title'] == "Build for One test build successful"
    assert (
        events[0]['msg_text']
        == "Build Number: 2\nDeployed To: buildhost42.dtdg.co\n\nMore Info: "
        + "http://localhost:8111/viewLog.html?buildId=2&buildTypeId=TestProject_TestBuild"
    )
    assert events[0]['tags'] == ['build', 'one:tag', 'one:test']
    assert events[0]['host'] == "buildhost42.dtdg.co"
    aggregator.reset()

    # One more check should not create any more events
    with patch('datadog_checks.base.utils.http.requests.get', get_mock_one_more_build):
        teamcity.check(CONFIG['instances'][0])

    assert len(aggregator.events) == 0


def get_mock_first_build(url, *args, **kwargs):
    mock_resp = MagicMock()
    if 'sinceBuild' in url:
        # looking for new builds
        json = {
            "count": 0,
            "href": (
                "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS"
            ),
        }
    else:
        json = {
            "count": 1,
            "href": "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,count:1",
            "nextHref": "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,count:1,start:1",
            "build": [
                {
                    "id": 1,
                    "buildTypeId": "TestProject_TestBuild",
                    "number": "1",
                    "status": "SUCCESS",
                    "state": "finished",
                    "href": "/guestAuth/app/rest/builds/id:1",
                    "webUrl": "http://localhost:8111/viewLog.html?buildId=1&buildTypeId=TestProject_TestBuild",
                }
            ],
        }

    mock_resp.json.return_value = json
    return mock_resp


def get_mock_one_more_build(url, *args, **kwargs):
    mock_resp = MagicMock()
    json = {}

    if 'sinceBuild:id:1' in url:
        json = {
            "count": 1,
            "href": "/guestAuth/app/rest/builds/?"
            + "locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS",
            "build": [
                {
                    "id": 2,
                    "buildTypeId": "TestProject_TestBuild",
                    "number": "2",
                    "status": "SUCCESS",
                    "state": "finished",
                    "href": "/guestAuth/app/rest/builds/id:2",
                    "webUrl": "http://localhost:8111/viewLog.html?buildId=2&buildTypeId=TestProject_TestBuild",
                }
            ],
        }
    elif 'sinceBuild:id:2' in url:
        json = {
            "count": 0,
            "href": (
                "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:2,status:SUCCESS"
            ),
        }

    mock_resp.json.return_value = json
    return mock_resp


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        ("legacy ssl config True", {'ssl_validation': True}, {'verify': True}),
        ("legacy ssl config False", {'ssl_validation': False}, {'verify': False}),
        ("legacy ssl config unset", {}, {'verify': True}),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(CONFIG['instances'][0])
    instance.update(extra_config)
    check = TeamCityCheck(CHECK_NAME, {}, [instance])

    with patch('datadog_checks.base.utils.http.requests.get') as r:
        check.check(instance)

        http_wargs = dict(
            auth=ANY,
            cert=ANY,
            headers=ANY,
            proxies=ANY,
            timeout=ANY,
            verify=ANY,
            allow_redirects=ANY,
        )
        http_wargs.update(expected_http_kwargs)

        r.assert_called_with(ANY, **http_wargs)


def mock_data(file):
    filepath = os.path.join(HERE, 'fixtures', file)
    with open(filepath, 'rb') as f:
        return f.read()


def test_metric_collection_build_config_stats(aggregator, instance, check):
    with patch('datadog_checks.teamcity.common.get_response', return_value=mock_data('build_stats.xml')):
        check = check(instance)
        check.check(instance)

    for metric_name in REST_METRICS:
        aggregator.assert_metric(metric_name)
        # aggregator.assert_metric_has_tag(metric_name, 'key1:value1')
