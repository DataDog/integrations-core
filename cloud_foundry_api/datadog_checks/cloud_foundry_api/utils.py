# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime
from typing import Any, Dict  # noqa: F401

from dateutil import parser, tz
from six.moves.urllib_parse import urljoin


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


def join_url(domain, path):
    # Make sure to have a trailing slash in domain, and no leading slash in path to avoid surprises with urljoin
    return urljoin(domain.rstrip("/") + "/", path.lstrip("/"))
