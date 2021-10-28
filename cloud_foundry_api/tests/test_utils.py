# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.cloud_foundry_api.utils import date_to_ts, get_next_url, join_url


def test_get_next_url():
    expected_next_url = "next_url"

    # v2
    next_url = get_next_url({"next_url": "next_url"}, "v2")
    assert next_url == expected_next_url

    # v3
    next_url = get_next_url({"pagination": {"next": "next_url"}}, "v3")
    assert next_url == expected_next_url

    # bad
    next_url = get_next_url({"bad": {"stuff": "next_url"}}, "v3")
    assert next_url == ""


def test_date_to_ts():
    expected_ts = 1591870273

    assert date_to_ts("2020-06-11T10:11:13,461Z") == expected_ts
    assert date_to_ts("2020-06-11T05:11:13,461-05:00") == expected_ts
    assert date_to_ts("2020-06-11T11:11:13,461+01:00") == expected_ts


def test_join_url():
    expected_url = "https://api.domain.com/v2/endpoint"

    assert join_url("https://api.domain.com/v2", "endpoint") == expected_url
    assert join_url("https://api.domain.com/v2/", "endpoint") == expected_url
    assert join_url("https://api.domain.com/v2", "/endpoint") == expected_url
    assert join_url("https://api.domain.com/v2/", "/endpoint") == expected_url
    assert join_url("https://api.domain.com/", "v2/endpoint") == expected_url
    assert join_url("https://api.domain.com", "v2/endpoint") == expected_url
    assert join_url("https://api.domain.com/", "/v2/endpoint") == expected_url
    assert join_url("https://api.domain.com", "/v2/endpoint") == expected_url
