# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import mock
import pytest
from requests.exceptions import HTTPError, RequestException

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.cloud_foundry_api import CloudFoundryApiCheck

from .constants import FREEZE_TIME


def test_check(aggregator, instance_v3, dd_events):
    # type: (AggregatorStub, Dict[str, Any], Dict[str, Any]) -> None

    with mock.patch.object(CloudFoundryApiCheck, "get_events", return_value=dd_events):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_v3])
        check.check({})

    aggregator.assert_metric(
        "cloud_foundry_api.events.count",
        3,
        tags=["api_url:https://api.sys.domain.com", "foo:bar"],
        metric_type=aggregator.COUNT,
        count=1,
    )
    aggregator.assert_event(count=1, **dd_events["event1"])
    aggregator.assert_event(count=1, **dd_events["event2"])
    aggregator.assert_all_metrics_covered()


def test_get_events(instance_v2, instance_v3, dd_events):
    # type: (AggregatorStub, Dict[str, Any], Dict[str, Any]) -> None
    scroll_pages_mock = mock.MagicMock(return_value=dd_events)
    with mock.patch.object(CloudFoundryApiCheck, "scroll_pages", scroll_pages_mock), mock.patch.object(
        CloudFoundryApiCheck, "get_oauth_token"
    ) as get_oauth_token_mock:
        check_v2 = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_v2])
        check_v3 = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_v3])

        def side_effect():
            check_v2._oauth_token = "oauth_token_v2"
            check_v3._oauth_token = "oauth_token_v3"

        get_oauth_token_mock.side_effect = side_effect

        events_v2 = check_v2.get_events()
        assert events_v2 == dd_events
        scroll_pages_mock.assert_called_once_with(
            "https://api.sys.domain.com/v2/events",
            {"q": "type IN audit1,audit2", "results-per-page": 45, "order-by": "timestamp", "order-direction": "desc"},
            {"Authorization": "Bearer oauth_token_v2"},
        )

        scroll_pages_mock.reset_mock()
        events_v3 = check_v3.get_events()
        assert events_v3 == dd_events
        scroll_pages_mock.assert_called_once_with(
            "https://api.sys.domain.com/v3/audit_events",
            {"types": "audit1,audit2", "per_page": 45, "order_by": "-created_at"},
            {"Authorization": "Bearer oauth_token_v3"},
        )


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
@mock.patch.object(CloudFoundryApiCheck, "http")
def test_scroll_pages(http_mock, _, aggregator, instance_v3, events_v3_p1, events_v3_p2):
    events_res_p1 = mock.MagicMock()
    events_res_p2 = mock.MagicMock()
    events_res_p1.json.return_value = events_v3_p1
    events_res_p2.json.return_value = events_v3_p2
    http_mock.get.side_effect = (events_res_p1, events_res_p2)

    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_v3])

    with mock.patch.object(check, "log") as log_mock:
        dd_events = check.scroll_pages("url", {"param": "foo"}, {"header": "bar"})

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
    dd_events = check.scroll_pages("url", {"param": "foo"}, {"header": "bar"})

    expected_calls = [(("url",), ({"params": {"param": "foo", "page": 1}, "headers": {"header": "bar"}}))]
    assert http_mock.get.call_args_list == expected_calls
    assert dd_events == {}

    aggregator.assert_service_check(
        name="cloud_foundry_api.api.can_connect",
        status=CloudFoundryApiCheck.OK,
        tags=["api_url:https://api.sys.domain.com", "foo:bar"],
        count=2,
    )


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
def test_scroll_pages_errors(_, aggregator, instance_v3, events_v3_p1):
    check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_v3])
    check._http = None  # initialize the _http attribute for mocking

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.side_effect = RequestException()
        check.scroll_pages("", {}, {})
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:https://api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(raise_for_status=mock.MagicMock(side_effect=HTTPError()))
        check.scroll_pages("", {}, {})
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:https://api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(check, "_http") as http_mock:
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(side_effect=ValueError()))
        check.scroll_pages("", {}, {})
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:https://api.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    # Getting an error in the middle of pagination still sends a critical service check,
    # but returns the events already gathered
    with mock.patch.object(check, "_http") as http_mock:
        events_res_p1 = mock.MagicMock()
        events_res_p1.json.return_value = events_v3_p1
        http_mock.get.side_effect = (events_res_p1, RequestException())
        dd_events = check.scroll_pages("", {}, {})
        aggregator.assert_service_check(
            name="cloud_foundry_api.api.can_connect",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:https://api.sys.domain.com", "foo:bar"],
            count=1,
        )
        assert len(dd_events) == 2


@mock.patch("datadog_checks.cloud_foundry_api.cloud_foundry_api.time.time", return_value=FREEZE_TIME)
def test_get_oauth_token(_, aggregator, instance_v3, oauth_token):
    with mock.patch.object(CloudFoundryApiCheck, "http") as http_mock:
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_v3])
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
            tags=["uaa_url:https://uaa.sys.domain.com", "foo:bar"],
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


def test_get_oauth_token_errors(aggregator, instance_v3):
    with mock.patch.object(CloudFoundryApiCheck, "http") as http_mock, pytest.raises(RequestException):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_v3])
        http_mock.get.side_effect = RequestException()
        check.get_oauth_token()
        aggregator.assert_service_check(
            name="cloud_foundry_api.uaa.can_authenticate",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:https://uaa.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(CloudFoundryApiCheck, "http") as http_mock, pytest.raises(HTTPError):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_v3])
        http_mock.get.return_value = mock.MagicMock(raise_for_status=mock.MagicMock(side_effect=HTTPError()))
        check.get_oauth_token()
        aggregator.assert_service_check(
            name="cloud_foundry_api.uaa.can_authenticate",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:https://uaa.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()

    with mock.patch.object(CloudFoundryApiCheck, "http") as http_mock, pytest.raises(ValueError):
        check = CloudFoundryApiCheck('cloud_foundry_api', {}, [instance_v3])
        http_mock.get.return_value = mock.MagicMock(json=mock.MagicMock(side_effect=ValueError()))
        check.get_oauth_token()
        aggregator.assert_service_check(
            name="cloud_foundry_api.uaa.can_authenticate",
            status=CloudFoundryApiCheck.CRITICAL,
            tags=["api_url:https://uaa.sys.domain.com", "foo:bar"],
            count=1,
        )
        aggregator.reset()
