# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# 3p
from mock import MagicMock, patch
import pytest

# project
from datadog_checks.teamcity import TeamCityCheck

CONFIG = {
    'instances': [{
        'name': 'One test build',
        'server': 'localhost:8111',
        'build_configuration': 'TestProject_TestBuild',
        'host_affected': 'buildhost42.dtdg.co',
        'basic_http_authentication': False,
        'is_deployment': False,
        'tags': ['one:tag', 'one:test'],
    }]
}


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.mark.integration
def test_build_event(aggregator):
    teamcity = TeamCityCheck('teamcity', {}, {})

    with patch('requests.get', get_mock_first_build):
        teamcity.check(CONFIG['instances'][0])

    assert len(aggregator.metric_names) == 0
    assert len(aggregator.events) == 0
    aggregator.reset()

    with patch('requests.get', get_mock_one_more_build):
        teamcity.check(CONFIG['instances'][0])

    events = aggregator.events
    assert len(events) == 1
    assert events[0]['msg_title'] == "Build for One test build successful"
    assert events[0]['msg_text'] == "Build Number: 2\nDeployed To: buildhost42.dtdg.co\n\nMore Info: " + \
                                    "http://localhost:8111/viewLog.html?buildId=2&buildTypeId=TestProject_TestBuild"
    assert events[0]['tags'] == ['build', 'one:tag', 'one:test']
    assert events[0]['host'] == "buildhost42.dtdg.co"
    aggregator.reset()

    # One more check should not create any more events
    with patch('requests.get', get_mock_one_more_build):
        teamcity.check(CONFIG['instances'][0])

    assert len(aggregator.events) == 0


def get_mock_first_build(url, *args, **kwargs):
    mock_resp = MagicMock()
    if 'sinceBuild' in url:
        # looking for new builds
        json = {
            "count": 0,
            "href": "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS"
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
                    "webUrl": "http://localhost:8111/viewLog.html?buildId=1&buildTypeId=TestProject_TestBuild"
                }
            ]
        }

    mock_resp.json.return_value = json
    return mock_resp


def get_mock_one_more_build(url, *args, **kwargs):
    mock_resp = MagicMock()
    json = {}

    if 'sinceBuild:id:1' in url:
        json = {
            "count": 1,
            "href": "/guestAuth/app/rest/builds/?" +
                    "locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS",
            "build": [
                {
                    "id": 2,
                    "buildTypeId": "TestProject_TestBuild",
                    "number": "2",
                    "status": "SUCCESS",
                    "state": "finished",
                    "href": "/guestAuth/app/rest/builds/id:2",
                    "webUrl": "http://localhost:8111/viewLog.html?buildId=2&buildTypeId=TestProject_TestBuild"
                }
            ]
        }
    elif 'sinceBuild:id:2' in url:
        json = {
            "count": 0,
            "href": "/guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:2,status:SUCCESS"
        }

    mock_resp.json.return_value = json
    return mock_resp
