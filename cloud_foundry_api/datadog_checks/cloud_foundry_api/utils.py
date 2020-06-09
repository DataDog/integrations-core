# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from dateutil import parser

from datadog_checks.base.types import Event

from .constants import SOURCE_TYPE_NAME


def parse_event_v3(cf_event):
    # type: (Dict[str, Any]) -> (Event, str, int)
    # Parse a v3 event
    # See http://v3-apidocs.cloudfoundry.org/version/3.84.0/index.html#list-audit-events for payload details.
    event_ts = int(parser.isoparse(cf_event["created_at"]).timestamp())
    event_guid = cf_event["guid"]
    target = cf_event["target"]
    actor = cf_event["actor"]

    dd_event = build_dd_event(
        cf_event["type"],
        event_guid,
        event_ts,
        actor["type"],
        actor["name"],
        actor["guid"],
        target["type"],
        target["name"],
        target["guid"],
        cf_event["space"]["guid"],
        cf_event["organization"]["guid"],
    )
    return dd_event, event_guid, event_ts


def parse_event_v2(cf_event):
    # type: (Dict[str, Any]) -> (Event, str, int)
    # Parse a v2 event
    # See https://apidocs.cloudfoundry.org/13.2.0/events/list_all_events.html for payload details.
    event_entity = cf_event["entity"]
    event_ts = int(parser.isoparse(event_entity["timestamp"]).timestamp())
    event_guid = cf_event["metadata"]["guid"]

    dd_event = build_dd_event(
        event_entity["type"],
        event_guid,
        event_ts,
        event_entity["actor_type"],
        event_entity["actor_name"],
        event_entity["actor"],
        event_entity["actee_type"],
        event_entity["actee_name"],
        event_entity["actee"],
        event_entity["space_guid"],
        event_entity["organization_guid"],
    )
    return dd_event, event_guid, event_ts


def build_dd_event(
    event_type,
    event_guid,
    event_ts,
    actor_type,
    actor_name,
    actor_guid,
    target_type,
    target_name,
    target_guid,
    space_guid,
    org_guid,
):
    # type: (str, str, int, str, str, str, str, str, str, str, str) -> Event
    tags = [
        "event_type:{}".format(event_type),
        "{}_name:{}".format(target_type, target_name),
        "{}_guid:{}".format(target_type, target_guid),
        "{}_name:{}".format(actor_type, actor_name),
        "{}_guid:{}".format(actor_type, actor_guid),
        "space_guid:{}".format(space_guid),
        "org_guid:{}".format(org_guid),
    ]
    dd_event = {
        "source_type_name": SOURCE_TYPE_NAME,
        "event_type": event_type,
        "timestamp": event_ts,
        "msg_title": "Event {} happened for {} {}".format(event_type, target_type, target_name),
        "msg_text": "Triggered by {} {}".format(actor_type, actor_name),
        "priority": "normal",
        "tags": tags,
        "aggregation_key": event_guid,  # In case we send duplicates for any reason, they'll be aggregated in the app
    }
    return dd_event
