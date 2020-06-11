# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import mock
import pytest
from requests.exceptions import HTTPError, RequestException

from datadog_checks.base.errors import CheckException, ConfigurationError
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.cloud_foundry_api import CloudFoundryApiCheck

from .constants import FREEZE_TIME


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
def test_init_defaults(_, instance_defaults):
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


@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v2", "uaa_url"))
def test_init(_, instance):
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
def test_check(_, aggregator, instance, dd_events):
    # type: (Any, AggregatorStub, Dict[str, Any], Dict[str, Any]) -> None

    with mock.patch.object(CloudFoundryApiCheck, "get_events", return_value=dd_events):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        check.check({})

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
def test_get_events(_, instance, dd_events):
    # type: (AggregatorStub, Dict[str, Any], Dict[str, Any]) -> None
    scroll_pages_mock = mock.MagicMock(return_value=dd_events)
    with mock.patch.object(CloudFoundryApiCheck, "scroll_pages", scroll_pages_mock), mock.patch.object(
        CloudFoundryApiCheck, "get_oauth_token"
    ) as get_oauth_token_mock:
        additional_tags = ["foo:bar"]
        check_v2 = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        check_v2._api_version = "v2"
        check_v3 = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
        check_v3._api_version = "v3"

        def side_effect():
            check_v2._oauth_token = "oauth_token_v2"
            check_v3._oauth_token = "oauth_token_v3"

        get_oauth_token_mock.side_effect = side_effect

        events_v2 = check_v2.get_events(additional_tags)
        assert events_v2 == dd_events
        scroll_pages_mock.assert_called_once_with(
            "https://api.sys.domain.com/v2/events",
            {"q": "type IN audit1,audit2", "results-per-page": 45, "order-by": "timestamp", "order-direction": "desc"},
            {"Authorization": "Bearer oauth_token_v2"},
            additional_tags,
        )

        scroll_pages_mock.reset_mock()
        events_v3 = check_v3.get_events(additional_tags)
        assert events_v3 == dd_events
        scroll_pages_mock.assert_called_once_with(
            "https://api.sys.domain.com/v3/audit_events",
            {"types": "audit1,audit2", "per_page": 45, "order_by": "-created_at"},
            {"Authorization": "Bearer oauth_token_v3"},
            additional_tags,
        )


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
@mock.patch.object(CloudFoundryApiCheck, "http")
def test_scroll_pages(http_mock, _, __, aggregator, instance, events_v3_p1, events_v3_p2):
    events_res_p1 = mock.MagicMock()
    events_res_p2 = mock.MagicMock()
    events_res_p1.json.return_value = events_v3_p1
    events_res_p2.json.return_value = events_v3_p2
    http_mock.get.side_effect = (events_res_p1, events_res_p2)

    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])

    with mock.patch.object(check, "log") as log_mock:
        dd_events = check.scroll_pages("url", {"param": "foo"}, {"header": "bar"}, [])

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

    # On second call, we don't collect any event, and don't go to the second page
    http_mock.reset_mock()
    # reset_mock doesn't reset side_effect or return_value, so manually reassign it
    http_mock.get.side_effect = (events_res_p1, events_res_p2)
    dd_events = check.scroll_pages("url", {"param": "foo"}, {"header": "bar"}, [])

    expected_calls = [(("url",), ({"params": {"param": "foo", "page": 1}, "headers": {"header": "bar"}}))]
    assert http_mock.get.call_args_list == expected_calls
    assert dd_events == {}

    aggregator.assert_service_check(
        name="cloud_foundry_api.api.can_connect",
        status=CloudFoundryApiCheck.OK,
        tags=["api_url:api.sys.domain.com", "foo:bar"],
        count=2,
    )


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "uaa_url"))
def test_scroll_pages_errors(_, __, aggregator, instance, events_v3_p1):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance])
    check._http = None  # initialize the _http attribute for mocking

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.side_effect = RequestException()
        check.scroll_pages("", {}, {}, [])
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(raise_for_status=mock.MagicMock(side_effect=HTTPError()))
        check.scroll_pages("", {}, {}, [])
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(side_effect=ValueError()))
        check.scroll_pages("", {}, {}, [])
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
        dd_events = check.scroll_pages("", {}, {}, [])
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:api.sys.domain.com", "foo:bar"],
            count=1,
        )
        assert len(dd_events) == 2


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
@mock.patch.object(CloudFoundryApiCheck, "discover_api", return_value=("v3", "https://uaa.sys.domain.com"))
@mock.patch.object(CloudFoundryApiCheck, "http")
def test_get_oauth_token(http_mock, _, __, aggregator, instance, oauth_token):
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
def test_get_oauth_token_errors(_, aggregator, instance):
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


def test_discover_api(api_info_v3, api_info_v2, instance):
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


def test_discover_api_errors(instance):
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
