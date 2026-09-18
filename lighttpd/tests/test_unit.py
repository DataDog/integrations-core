# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pytest

from datadog_checks.lighttpd import Lighttpd

pytestmark = pytest.mark.unit


def test_url_suffix_per_version_mapping():
    assert Lighttpd.URL_SUFFIX_PER_VERSION == {1: "?auto", 2: "?format=plain", "Unknown": "?auto"}


def test_service_check_tags_use_default_port_80_when_url_has_no_port(aggregator, mock_http_response):
    mock_http_response(content="IdleServers: 5\n")
    url = "http://lighttpd.example.com/server-status"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    check.check({"lighttpd_status_url": url})
    aggregator.assert_service_check(
        check.SERVICE_CHECK_NAME,
        status=Lighttpd.OK,
        tags=["host:lighttpd.example.com", "port:80"],
    )


def test_check_raises_directly_without_retry_when_url_already_has_suffix(mock_http_response):
    mock_get = mock_http_response(content="")
    url = "http://lighttpd.example.com/server-status?auto"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    expected_message = "No metrics were fetched for this instance. Make sure that {} is the proper url.".format(url)

    with pytest.raises(Exception, match=re.escape(expected_message)):
        check.check({"lighttpd_status_url": url})

    assert mock_get.call_count == 1


def test_unparseable_value_is_skipped_not_break(aggregator, mock_http_response):
    mock_http_response(content="IdleServers: not-a-number\nBusyServers: 4\n")
    url = "http://lighttpd.example.com/server-status"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    check.check({"lighttpd_status_url": url})
    aggregator.assert_metric("lighttpd.performance.busy_servers", value=4)


def test_total_kbytes_converted_to_bytes_only_for_that_metric(aggregator, mock_http_response):
    mock_http_response(content="Total kBytes: 5\nIdleServers: 3\nUptime: 7\n")
    url = "http://lighttpd.example.com/server-status"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    check.check({"lighttpd_status_url": url})

    aggregator.assert_metric("lighttpd.net.bytes", value=5120)
    aggregator.assert_metric("lighttpd.net.bytes_per_s", value=5120)
    aggregator.assert_metric("lighttpd.performance.idle_server", value=3)
    aggregator.assert_metric("lighttpd.performance.uptime", value=7)


def test_single_gauge_match_avoids_false_no_metrics_exception(mock_http_response):
    mock_http_response(content="IdleServers: 5\n")
    url = "http://lighttpd.example.com/server-status?auto"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    check.check({"lighttpd_status_url": url})


def test_single_counter_match_avoids_false_no_metrics_exception(mock_http_response):
    mock_http_response(content="requests_abs: 5\n")
    url = "http://lighttpd.example.com/server-status?auto"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    check.check({"lighttpd_status_url": url})


def test_service_check_critical_when_http_request_fails(aggregator, mock_http_response):
    mock_http_response(status_code=500)
    url = "http://lighttpd.example.com/server-status"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    with pytest.raises(Exception):
        check.check({"lighttpd_status_url": url})
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Lighttpd.CRITICAL)


def test_version_metadata_uses_correct_regex_groups(datadog_agent, mock_http_response):
    mock_http_response(content="IdleServers: 5\n", headers={"server": "lighttpd/1.4.55"})
    url = "http://lighttpd.example.com/server-status"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    check.check_id = "test:123"
    check.check({"lighttpd_status_url": url})

    datadog_agent.assert_metadata("test:123", {"version.raw": "1.4.55"})


def test_line_with_extra_colon_is_ignored_not_unpacked(mock_http_response):
    mock_http_response(content="a: b: c\nIdleServers: 5\n")
    url = "http://lighttpd.example.com/server-status?auto"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    check.check({"lighttpd_status_url": url})


def test_check_retries_once_then_raises_when_suffix_missing_and_url_sorts_higher(mock_http_response):
    mock_get = mock_http_response(content="")
    url = "http://lighttpd.example.com/server-status~auto"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    expected_message = "No metrics were fetched for this instance. Make sure that {} is the proper url.".format(url)

    with pytest.raises(Exception, match=re.escape(expected_message)):
        check.check({"lighttpd_status_url": url})
    assert mock_get.call_count == 2


def test_check_retries_once_then_raises_when_suffix_missing_and_url_sorts_lower(mock_http_response):
    mock_get = mock_http_response(content="")
    url = "http://lighttpd.example.com/server-status!auto"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    expected_message = "No metrics were fetched for this instance. Make sure that {} is the proper url.".format(url)

    with pytest.raises(Exception, match=re.escape(expected_message)):
        check.check({"lighttpd_status_url": url})
    assert mock_get.call_count == 2


def test_check_raises_immediately_when_url_already_marked_as_assumed(mock_http_response):
    mock_get = mock_http_response(content="")
    url = "http://lighttpd.example.com/server-status!auto"
    check = Lighttpd("lighttpd", {}, [{"lighttpd_status_url": url}])
    check.assumed_url[url] = url + "?auto"
    expected_message = "No metrics were fetched for this instance. Make sure that {} is the proper url.".format(url)

    with pytest.raises(Exception, match=re.escape(expected_message)):
        check.check({"lighttpd_status_url": url})
    assert mock_get.call_count == 1
