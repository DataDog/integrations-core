# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dateutil import parser

from datadog_checks.base.types import Event

from .constants import SOURCE_TYPE_NAME


def parse_event_v3(cf_event):
    # Parse a v3 event
    # See http://v3-apidocs.cloudfoundry.org/version/3.84.0/index.html#list-audit-events for payload details.
    event_ts = int(parser.isoparse(cf_event["created_at"]).timestamp())
    event_guid = cf_event["guid"]
    target = cf_event["target"]
    actor = cf_event["actor"]
    tags = [
        "event_type:{}".format(cf_event["type"]),
        "{}_name:{}".format(target["type"], target["name"]),
        "{}_guid:{}".format(target["type"], target["guid"]),
        "{}_name:{}".format(actor["type"], actor["name"]),
        "{}_guid:{}".format(actor["type"], actor["guid"]),
        "space_guid:{}".format(cf_event["space"]["guid"]),
        "org_guid:{}".format(cf_event["organization"]["guid"]),
    ]
    dd_event = Event(
        {
            "source_type_name": SOURCE_TYPE_NAME,
            "event_type": cf_event["type"],
            "timestamp": event_ts,
            "msg_title": "Event {} happened for {} {}".format(cf_event["type"], target["type"], actor["name"]),
            "msg_text": "Triggered by {} {}".format(actor["type"], actor["name"]),
            "priority": "normal",
            "tags": tags,
        }
    )
    return dd_event, event_guid, event_ts


def parse_event_v2(cf_event):
    # Parse a v2 event
    # See https://apidocs.cloudfoundry.org/13.2.0/events/list_all_events.html for payload details.
    event_entity = cf_event["entity"]
    event_ts = int(parser.isoparse(event_entity["timestamp"]).timestamp())
    event_guid = cf_event["metadata"]["guid"]

    tags = [
        "event_type:{}".format(event_entity["type"]),
        "{}_name:{}".format(event_entity["actee_type"], event_entity["actee_name"]),
        "{}_guid:{}".format(event_entity["actee_type"], event_entity["actee"]),
        "{}_name:{}".format(event_entity["actor_type"], event_entity["actor_name"]),
        "{}_guid:{}".format(event_entity["actor_type"], event_entity["actor"]),
        "space_guid:{}".format(event_entity["space_guid"]),
        "org_guid:{}".format(event_entity["organization_guid"]),
    ]
    dd_event = Event(
        {
            "source_type_name": SOURCE_TYPE_NAME,
            "event_type": event_entity["type"],
            "timestamp": event_ts,
            "msg_title": "Event {} happened for {} {}".format(
                event_entity["type"], event_entity["actee_type"], event_entity["actee_name"]
            ),
            "msg_text": "Triggered by {} {}".format(event_entity["actor_type"], event_entity["actor_name"]),
            "priority": "normal",
            "tags": tags,
        }
    )
    return dd_event, event_guid, event_ts
