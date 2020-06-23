# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime
from typing import Any, Dict, List, Tuple

from dateutil import parser, tz

from datadog_checks.base.types import Event

from .constants import SOURCE_TYPE_NAME


def parse_event(cf_event, api_version, additional_tags):
    # type: (Dict[str, Any], str, List[str]) -> Tuple[Event, str, int]
    dd_event = {}
    event_guid = ""
    event_ts = 0

    if api_version == "v2":
        # Parse a v2 event
        # See https://apidocs.cloudfoundry.org/13.2.0/events/list_all_events.html for payload details.
        event_entity = cf_event["entity"]
        event_ts = date_to_ts(event_entity["timestamp"])
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
            event_entity.get("space_guid"),  # Some events might not have a space associated
            event_entity.get("organization_guid"),  # Some events might not have an org associated
            additional_tags,
        )
    elif api_version == "v3":
        # Parse a v3 event
        # See http://v3-apidocs.cloudfoundry.org/version/3.84.0/index.html#list-audit-events for payload details.
        event_ts = date_to_ts(cf_event["created_at"])
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
            cf_event.get("space", {}).get("guid"),  # Some events might not have a space associated
            cf_event.get("organization", {}).get("guid"),  # Some events might not have an org associated
            additional_tags,
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
    additional_tags,
):
    # type: (str, str, int, str, str, str, str, str, str, str, str, List[str]) -> Event
    tags = [
        "event_type:{}".format(event_type),
        "{}_name:{}".format(target_type, target_name),
        "{}_guid:{}".format(target_type, target_guid),
        "{}_name:{}".format(actor_type, actor_name),
        "{}_guid:{}".format(actor_type, actor_guid),
        "space_guid:{}".format(space_guid),
        "org_guid:{}".format(org_guid),
    ] + additional_tags
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


def get_next_url(payload, version):
    # type: (Dict[str, Any], str) -> str
    next_url = ""
    if version == "v2":
        next_url = payload.get("next_url", "")
    elif version == "v3":
        next_url = payload.get("pagination", {}).get("next", "")
    return next_url


def date_to_ts(iso_string):
    # type: (str) -> int
    return int((parser.isoparse(iso_string) - datetime(1970, 1, 1, tzinfo=tz.UTC)).total_seconds())
