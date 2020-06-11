# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.cloud_foundry_api.utils import build_dd_event, date_to_ts, get_next_url, parse_event

from .constants import FREEZE_TIME


@mock.patch("datadog_checks.cloud_foundry_api.utils.build_dd_event")
def test_parse_event(build_dd_event_mock, event_v2, event_v3):
    # v2
    _, event_guid, event_ts = parse_event(event_v2, "v2")
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
    )

    # v3
    build_dd_event_mock.reset_mock()
    _, event_guid, event_ts = parse_event(event_v3, "v3")
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
    )


def test_build_dd_event():
    event = build_dd_event(
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
    )
    tags = [
        "event_type:event_type",
        "target_type_name:target_name",
        "target_type_guid:target_guid",
        "actor_type_name:actor_name",
        "actor_type_guid:actor_guid",
        "space_guid:space_guid",
        "org_guid:org_guid",
    ]
    expected_event = {
        "source_type_name": "Cloud Foundry",
        "event_type": "event_type",
        "timestamp": 1234,
        "msg_title": "Event event_type happened for target_type target_name",
        "msg_text": "Triggered by actor_type actor_name",
        "priority": "normal",
        "tags": tags,
        "aggregation_key": "event_guid",
    }
    assert event == expected_event


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
