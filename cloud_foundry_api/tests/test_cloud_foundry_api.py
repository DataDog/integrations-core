# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from requests.exceptions import HTTPError, RequestException

from datadog_checks.base.errors import CheckException, ConfigurationError
from datadog_checks.cloud_foundry_api import CloudFoundryApiCheck

from .constants import FREEZE_TIME


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_id": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_id": "space_name"})
def test_init_defaults(_, __, ___, instance_defaults):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_defaults])
    assert check._api_url == "https://api.sys.domain.com"
    assert check._client_id == "client_id"
    assert check._client_secret == "client_secret"
    assert check._event_filter == "audit.app.restage,audit.app.update,audit.app.create,app.crash"
    assert check._tags == []
    assert check._per_page == 100
    assert check._api_version == "v3"
    assert check._uaa_url == "uaa_url"
    assert check._last_event_guid == ""
    assert check._last_event_ts == 0
    assert check._oauth_token == ""
    assert check._token_expiration == 0
    assert check._orgs == {"org_id": "org_name"}
    assert check._spaces == {"space_id": "space_name"}


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v2", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_id": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_id": "space_name"})
def test_init(_, __, ___, instance):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    assert check._api_url == "https://api.sys.domain.com"
    assert check._client_id == "client_id"
    assert check._client_secret == "client_secret"
    assert check._event_filter == "audit1,audit2"
    assert check._tags == ["foo:bar"]
    assert check._per_page == 45
    assert check._api_version == "v2"
    assert check._uaa_url == "uaa_url"
    assert check._last_event_guid == ""
    assert check._last_event_ts == 0
    assert check._oauth_token == ""
    assert check._token_expiration == 0
    assert check._orgs == {"org_id": "org_name"}
    assert check._spaces == {"space_id": "space_name"}


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v2", "uaa_url"))
def test_init_bad_instance(_):
    # No api_url
    instance = {}
    with pytest.raises(ConfigurationError, match="`api_url`"):
        CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])

    # No client_id
    instance["api_url"] = "api_url"
    with pytest.raises(ConfigurationError, match="`client_id`"):
        CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])

    # No client_secret
    instance["client_id"] = "client_id"
    with pytest.raises(ConfigurationError, match="`client_secret`"):
        CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_id": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_id": "space_name"})
def test_check(_, __, ___, aggregator, instance, dd_events, dd_run_check):
    with mock.patch.object(CloudFoundryApiCheck, "get_events", return_value=dd_events):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        dd_run_check(check)

    aggregator.assert_metric(
        "cloud_foundry_api.events.count",
        3,
        tags=["api_url:api.sys.domain.com", "foo:bar"],
        metric_type=aggregator.COUNT,
        count=1,
    )
    aggregator.assert_event(count=1, **dd_events["event1"])
    aggregator.assert_event(count=1, **dd_events["event2"])
    aggregator.assert_all_metrics_covered()


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_id": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_id": "space_name"})
def test_get_events(_, __, ___, instance, dd_events):
    scroll_events_mock = mock.MagicMock(return_value=dd_events)
    with mock.patch.object(CloudFoundryApiCheck, "scroll_events", scroll_events_mock), mock.patch.object(
        CloudFoundryApiCheck, "get_oauth_token"
    ) as get_oauth_token_mock:
        check_v2 = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        check_v2._api_version = "v2"
        check_v3 = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        check_v3._api_version = "v3"

        def side_effect():
            check_v2._oauth_token = "oauth_token_v2"
            check_v3._oauth_token = "oauth_token_v3"

        get_oauth_token_mock.side_effect = side_effect

        events_v2 = check_v2.get_events()
        assert events_v2 == dd_events
        scroll_events_mock.assert_called_once_with(
            "https://api.sys.domain.com/v2/events",
            {"q": "type IN audit1,audit2", "results-per-page": 45, "order-by": "timestamp", "order-direction": "desc"},
            {"Authorization": "Bearer oauth_token_v2"},
        )

        scroll_events_mock.reset_mock()
        events_v3 = check_v3.get_events()
        assert events_v3 == dd_events
        scroll_events_mock.assert_called_once_with(
            "https://api.sys.domain.com/v3/audit_events",
            {"types": "audit1,audit2", "per_page": 45, "order_by": "-created_at"},
            {"Authorization": "Bearer oauth_token_v3"},
        )


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"7b6fdcb8-c2c2-4b2c-9c9a-682de9cf607f": "org_name"})
@mock.patch.object(
    CloudFoundryApiCheck, "get_spaces", return_value={"fe712d4e-91a9-46f2-b82c-fa26da40dc53": "space_name"}
)
@mock.patch.object(CloudFoundryApiCheck, "http")
def test_scroll_events(http_mock, _, __, ___, ____, aggregator, instance, events_v3_p0, events_v3_p1, events_v3_p2):
    events_res_p0 = mock.MagicMock()
    events_res_p1 = mock.MagicMock()
    events_res_p2 = mock.MagicMock()
    events_res_p0.json.return_value = events_v3_p0
    events_res_p1.json.return_value = events_v3_p1
    events_res_p2.json.return_value = events_v3_p2
    http_mock.get.side_effect = (events_res_p1, events_res_p2)

    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])

    with mock.patch.object(check, "log") as log_mock:
        dd_events = check.scroll_events("url", {"param": "foo"}, {"header": "bar"})

    expected_calls = [
        (("url",), ({"params": {"param": "foo", "page": 1}, "headers": {"header": "bar"}})),
        (("url",), ({"params": {"param": "foo", "page": 2}, "headers": {"header": "bar"}})),
    ]
    assert http_mock.get.call_args_list == expected_calls
    # Only 3 events collected, the fourth one is too old
    assert len(dd_events) == 3
    # The bad event is skipped
    log_mock.exception.assert_called_once()
    assert "Could not parse event" in log_mock.exception.call_args[0][0]

    # On second call, we collect only new events from page 0, and don't go to the second page
    http_mock.reset_mock()
    # reset_mock doesn't reset side_effect or return_value, so manually reassign it
    http_mock.get.side_effect = (events_res_p0, events_res_p1)
    dd_events = check.scroll_events("url", {"param": "foo"}, {"header": "bar"})

    expected_calls = [(("url",), ({"params": {"param": "foo", "page": 1}, "headers": {"header": "bar"}}))]
    assert http_mock.get.call_args_list == expected_calls
    assert len(dd_events) == 1

    aggregator.assert_service_check(
        name="cloud_foundry_api.api.can_connect",
        status=CloudFoundryApiCheck.OK,
        tags=["api_url:api.sys.domain.com", "foo:bar"],
        count=2,
    )


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"7b6fdcb8-c2c2-4b2c-9c9a-682de9cf607f": "org_name"})
@mock.patch.object(
    CloudFoundryApiCheck, "get_spaces", return_value={"fe712d4e-91a9-46f2-b82c-fa26da40dc53": "space_name"}
)
@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
def test_scroll_events_errors(_, __, ___, ____, aggregator, instance, events_v3_p1):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    check._http = None  # initialize the _http attribute for mocking

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.side_effect = RequestException()
        check.scroll_events("", {}, {})
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(raise_for_status=mock.MagicMock(side_effect=HTTPError()))
        check.scroll_events("", {}, {})
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(side_effect=ValueError()))
        check.scroll_events("", {}, {})
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    # Getting an error in the middle of pagination still sends a critical service check,
    # but returns the events already gathered
    with mock.patch.object(check, "_http") as http_mock:
        events_res_p1 = mock.MagicMock()
        events_res_p1.json.return_value = events_v3_p1
        http_mock.get.side_effect = (events_res_p1, RequestException())
        dd_events = check.scroll_events("", {}, {})
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        assert len(dd_events) == 2


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "https://uaa.sys.domain.com"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={})
@mock.patch.object(CloudFoundryApiCheck, "http")
def test_get_oauth_token(http_mock, _, __, ___, ____, aggregator, instance, oauth_token):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    oauth_res = mock.MagicMock()
    oauth_res.json.return_value = oauth_token
    http_mock.get.return_value = oauth_res

    # Token gets fetched properly
    check.get_oauth_token()
    assert check._oauth_token == "token"
    assert check._token_expiration == FREEZE_TIME + 1000
    aggregator.assert_service_check(
        name="cloud_foundry_api.uaa.can_authenticate",
        status=CloudFoundryApiCheck.OK,
        tags=["uaa_url:uaa.sys.domain.com", "foo:bar", "api_url:api.sys.domain.com"],
        count=1,
    )

    # Token doesn't get refreshed if not needed
    check._oauth_token = "no_refresh"
    check._token_expiration = FREEZE_TIME + 1234
    check.get_oauth_token()
    assert check._oauth_token == "no_refresh"
    assert check._token_expiration == FREEZE_TIME + 1234

    # Token gets refreshed if soon to be expired
    check._oauth_token = "no_refresh"
    check._token_expiration = FREEZE_TIME + 299
    check.get_oauth_token()
    assert check._oauth_token == "token"
    assert check._token_expiration == FREEZE_TIME + 1000


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "https://uaa.sys.domain.com"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={})
def test_get_oauth_token_errors(_, __, ___, aggregator, instance):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    check._http = None  # initialize the _http attribute for mocking

    with mock.patch.object(check, "_http") as http_mock, pytest.raises(RequestException):
        http_mock.get.side_effect = RequestException()
        check.get_oauth_token()
        aggregator.assert_service_check(
            name="cloud_foundry_api.uaa.can_authenticate",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["uaa_url:uaa.sys.domain.com", "foo:bar", "api_url:api.sys.domain.com"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock, pytest.raises(HTTPError):
        http_mock.get.return_value = mock.MagicMock(raise_for_status=mock.MagicMock(side_effect=HTTPError()))
        check.get_oauth_token()
        aggregator.assert_service_check(
            name="cloud_foundry_api.uaa.can_authenticate",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["uaa_url:uaa.sys.domain.com", "foo:bar", "api_url:api.sys.domain.com"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock, pytest.raises(ValueError):
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(side_effect=ValueError()))
        check.get_oauth_token()
        aggregator.assert_service_check(
            name="cloud_foundry_api.uaa.can_authenticate",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["uaa_url:uaa.sys.domain.com", "foo:bar", "api_url:api.sys.domain.com"],
            count=1,
        )
        aggregator.reset()


@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={})
def test_discover_api(_, __, api_info_v3, api_info_v2, instance):
    # Mock for creating the instance only
    with mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url")):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    check._http = None  # initialize the _http attribute for mocking

    # v2
    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(return_value=api_info_v2))
        api_version, uaa_url = check.discover_api()
        assert api_version == "v2"
        assert uaa_url == "https://uaa.sys.domain.com"
    # v3
    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(return_value=api_info_v3))
        api_version, uaa_url = check.discover_api()
        assert api_version == "v3"
        assert uaa_url == "https://uaa.sys.domain.com"


@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={})
def test_discover_api_errors(_, __, instance):
    # Mock for creating the instance only
    with mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url")):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    check._http = None  # initialize the _http attribute for mocking

    with mock.patch.object(check, "_http") as http_mock, pytest.raises(RequestException):
        http_mock.get.side_effect = RequestException()
        check.discover_api()

    with mock.patch.object(check, "_http") as http_mock, pytest.raises(HTTPError):
        http_mock.get.return_value = mock.MagicMock(raise_for_status=mock.MagicMock(side_effect=HTTPError()))
        check.discover_api()

    with mock.patch.object(check, "_http") as http_mock, pytest.raises(ValueError):
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(side_effect=ValueError()))
        check.discover_api()

    with mock.patch.object(check, "_http") as http_mock, pytest.raises(CheckException):
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(return_value={"no_links": None}))
        check.discover_api()

    with mock.patch.object(check, "_http") as http_mock, pytest.raises(CheckException):
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(return_value={"links": {"no_uaa": None}}))
        check.discover_api()


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={})
@mock.patch.object(CloudFoundryApiCheck, "build_dd_event")
def test_parse_event(build_dd_event_mock, _, __, ___, ____, event_v2, event_v3, instance):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])

    # v2
    check._api_version = "v2"
    _, event_guid, event_ts = check.parse_event(event_v2)
    assert event_guid == "event_guid"
    assert event_ts == FREEZE_TIME
    build_dd_event_mock.assert_called_once_with(
        "event_type",
        "event_guid",
        FREEZE_TIME,
        "actor_type",
        "actor_name",
        "actor_guid",
        "target_type",
        "target_name",
        "target_guid",
        "space_guid",
        "org_guid",
        {"some": "metadata"},
    )

    # v3
    check._api_version = "v3"
    build_dd_event_mock.reset_mock()
    _, event_guid, event_ts = check.parse_event(event_v3)
    assert event_guid == "event_guid"
    assert event_ts == FREEZE_TIME
    build_dd_event_mock.assert_called_once_with(
        "event_type",
        "event_guid",
        FREEZE_TIME,
        "actor_type",
        "actor_name",
        "actor_guid",
        "target_type",
        "target_name",
        "target_guid",
        "space_guid",
        "org_guid",
        {"some": "metadata"},
    )


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_guid": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_guid": "space_name"})
def test_build_dd_event(_, __, ___, instance):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    event = check.build_dd_event(
        "event_type",
        "event_guid",
        1234,
        "actor_type",
        "actor_name",
        "actor_guid",
        "target_type",
        "target_name",
        "target_guid",
        "space_guid",
        "org_guid",
        {"some": "metadata"},
    )
    tags = [
        "event_type:event_type",
        "target_type_name:target_name",
        "target_type_guid:target_guid",
        "actor_type_name:actor_name",
        "actor_type_guid:actor_guid",
        "space_guid:space_guid",
        "space_id:space_guid",
        "space_name:space_name",
        "org_guid:org_guid",
        "org_id:org_guid",
        "org_name:org_name",
        "foo:bar",
    ]
    expected_event = {
        "source_type_name": "Cloud Foundry",
        "event_type": "event_type",
        "timestamp": 1234,
        "msg_title": "Event event_type happened for target_type target_name",
        "msg_text": "%%% \n Triggered by actor_type actor_name\n\n"
        + "Metadata:\n```\n{\n  \"some\": \"metadata\"\n}\n``` \n %%%",
        "priority": "normal",
        "tags": tags,
        "aggregation_key": "event_guid",
    }
    assert event == expected_event

    # With no space and org and metadata
    event = check.build_dd_event(
        "event_type",
        "event_guid",
        1234,
        "actor_type",
        "actor_name",
        "actor_guid",
        "target_type",
        "target_name",
        "target_guid",
        "",
        "",
        {},
    )
    tags = [
        "event_type:event_type",
        "target_type_name:target_name",
        "target_type_guid:target_guid",
        "actor_type_name:actor_name",
        "actor_type_guid:actor_guid",
        "space_guid:none",
        "space_id:none",
        "space_name:none",
        "org_guid:none",
        "org_id:none",
        "org_name:none",
        "foo:bar",
    ]
    expected_event = {
        "source_type_name": "Cloud Foundry",
        "event_type": "event_type",
        "timestamp": 1234,
        "msg_title": "Event event_type happened for target_type target_name",
        "msg_text": "%%% \n Triggered by actor_type actor_name\n\nMetadata:\n```\n{}\n``` \n %%%",
        "priority": "normal",
        "tags": tags,
        "aggregation_key": "event_guid",
    }
    assert event == expected_event


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_guid": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_guid": "space_name"})
@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.get_next_url", side_effect=["next", ""])
@mock.patch.object(CloudFoundryApiCheck, "http")
def test_scroll_api_pages(http_mock, get_next_url_mock, __, ___, ____, aggregator, instance):

    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])

    # When exhausting all pages
    for _ in check.scroll_api_pages("api_url", {}, {}):
        pass

    assert http_mock.get.call_args_list == [
        mock.call("api_url", params={"page": 1}, headers={}),
        mock.call("api_url", params={"page": 2}, headers={}),
    ]
    aggregator.assert_service_check(
        "cloud_foundry_api.api.can_connect", count=1, tags=["api_url:api.sys.domain.com", "foo:bar"]
    )

    # When breaking in the middle of pagination
    http_mock.get.reset_mock()
    aggregator.reset()
    get_next_url_mock.side_effect = ["next", ""]
    for _ in check.scroll_api_pages("api_url", {}, {}):
        break

    assert http_mock.get.call_args_list == [mock.call("api_url", params={"page": 1}, headers={})]
    aggregator.assert_service_check(
        "cloud_foundry_api.api.can_connect",
        status=CloudFoundryApiCheck.OK,
        count=1,
        tags=["api_url:api.sys.domain.com", "foo:bar"],
    )


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_guid": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_guid": "space_name"})
def test_scroll_api_pages_errors(_, __, ___, aggregator, instance):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    check._http = None

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.side_effect = RequestException()
        for _ in check.scroll_api_pages("", {}, {}):
            pass
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.assert_service_check(
            "cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.OK,
            count=0,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(raise_for_status=mock.MagicMock(side_effect=HTTPError()))
        for _ in check.scroll_api_pages("", {}, {}):
            pass
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.assert_service_check(
            "cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.OK,
            count=0,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(side_effect=ValueError()))
        for _ in check.scroll_api_pages("", {}, {}):
            pass
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.assert_service_check(
            "cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.OK,
            count=0,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
        )
        aggregator.reset()


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={})
def test_get_orgs(_, __, instance, orgs_v2_p1, orgs_v2_p2, orgs_v3_p1, orgs_v3_p2):
    expected_orgs = {
        "671557cf-edcd-49df-9863-ee14513d13c7": "org_1",
        "8c19a50e-7974-4c67-adea-9640fae21526": "org_2",
        "321c58b0-777b-472f-812e-c08c53817074": "org_3",
        "0ba4c8cb-9e71-4d6e-b6ff-74e301ed6467": "org_4",
    }
    with mock.patch.object(
        CloudFoundryApiCheck, "scroll_api_pages", return_value=[orgs_v2_p1, orgs_v2_p2]
    ), mock.patch.object(CloudFoundryApiCheck, "get_oauth_token"):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        check._api_version = "v2"

        assert check.get_orgs() == expected_orgs

    with mock.patch.object(
        CloudFoundryApiCheck, "scroll_api_pages", return_value=[orgs_v3_p1, orgs_v3_p2]
    ), mock.patch.object(CloudFoundryApiCheck, "get_oauth_token"):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        check._api_version = "v3"

        assert check.get_orgs() == expected_orgs


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={})
def test_get_spaces(_, __, instance, spaces_v2_p1, spaces_v2_p2, spaces_v3_p1, spaces_v3_p2):
    expected_spaces = {
        "417b893e-291e-48ec-94c7-7b2348604365": "space_1",
        "1b8dcf2e-ed92-4daa-b9fb-0fa5a97b9289": "space_2",
        "d5d005a4-0320-4daa-ac0a-81f8dcd00fe0": "space_3",
        "8c7e64bb-0bf8-4a7a-92e1-2fe06e7ec793": "space_4",
    }
    with mock.patch.object(
        CloudFoundryApiCheck, "scroll_api_pages", return_value=[spaces_v2_p1, spaces_v2_p2]
    ), mock.patch.object(CloudFoundryApiCheck, "get_oauth_token"):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        check._api_version = "v2"

        assert check.get_spaces() == expected_spaces

    with mock.patch.object(
        CloudFoundryApiCheck, "scroll_api_pages", return_value=[spaces_v3_p1, spaces_v3_p2]
    ), mock.patch.object(CloudFoundryApiCheck, "get_oauth_token"):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        check._api_version = "v3"

        assert check.get_spaces() == expected_spaces


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_guid": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_guid": "space_name"})
@mock.patch.object(CloudFoundryApiCheck, "http")
def test_get_org_name(http_mock, _, __, ___, instance, org_v2, org_v3):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    with mock.patch.object(check, "get_oauth_token"), mock.patch.object(check, "log") as log_mock:
        # Cache access
        assert check._orgs["org_guid"] == "org_name"
        assert check.get_org_name("org_guid") == "org_name"
        http_mock.get.assert_not_called()

        # Cache miss
        # v2
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(return_value=org_v2))
        check._api_version = "v2"
        assert check.get_org_name("new_id") == "org_1"
        assert check._orgs["new_id"] == "org_1"
        http_mock.get.assert_called_once_with(
            "https://api.sys.domain.com/v2/organizations/new_id",
            headers={"Authorization": "Bearer {}".format(check._oauth_token)},
        )
        # v3
        http_mock.get.reset_mock()
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(return_value=org_v3))
        check._api_version = "v3"
        assert check.get_org_name("new_id_2") == "org_1"
        assert check._orgs["new_id_2"] == "org_1"
        http_mock.get.assert_called_once_with(
            "https://api.sys.domain.com/v3/organizations/new_id_2",
            headers={"Authorization": "Bearer {}".format(check._oauth_token)},
        )
        # Error
        http_mock.get.side_effect = RequestException
        assert check.get_org_name("id_error") is None
        log_mock.exception.assert_called_once()


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_guid": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_guid": "space_name"})
@mock.patch.object(CloudFoundryApiCheck, "http")
def test_get_space_name(http_mock, _, __, ___, instance, space_v2, space_v3):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    with mock.patch.object(check, "get_oauth_token"), mock.patch.object(check, "log") as log_mock:
        # Cache access
        assert check._spaces["space_guid"] == "space_name"
        assert check.get_space_name("space_guid") == "space_name"
        http_mock.get.assert_not_called()

        # Cache miss
        # v2
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(return_value=space_v2))
        check._api_version = "v2"
        assert check.get_space_name("new_id") == "space_1"
        assert check._spaces["new_id"] == "space_1"
        http_mock.get.assert_called_once_with(
            "https://api.sys.domain.com/v2/spaces/new_id",
            headers={"Authorization": "Bearer {}".format(check._oauth_token)},
        )
        # v3
        http_mock.get.reset_mock()
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(return_value=space_v3))
        check._api_version = "v3"
        assert check.get_space_name("new_id_2") == "space_1"
        assert check._spaces["new_id_2"] == "space_1"
        http_mock.get.assert_called_once_with(
            "https://api.sys.domain.com/v3/spaces/new_id_2",
            headers={"Authorization": "Bearer {}".format(check._oauth_token)},
        )
        # Error
        http_mock.get.side_effect = RequestException
        assert check.get_space_name("id_error") is None
        log_mock.exception.assert_called_once()


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "get_orgs", return_value={"org_guid": "org_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_spaces", return_value={"space_guid": "space_name"})
@mock.patch.object(CloudFoundryApiCheck, "get_oauth_token")
def test_get_auth_headers(_, __, ___, ____, instance):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    check._oauth_token = "oauth_token"
    assert check.get_auth_header() == {"Authorization": "Bearer oauth_token"}
