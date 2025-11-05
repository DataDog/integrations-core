# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import string
from typing import Optional


def is_affirmative(val: str) -> bool:
    return "yes" in val.lower()


def transform_status(status: str) -> int:
    return int(status == "ok")


def transform_float(val: str) -> float:
    if val == "-":
        return -1
    else:
        val = val.rstrip(string.ascii_letters + string.punctuation)
        return float(val)


def transform_runtime(val: str) -> float:
    if val == "UNLIMITED":
        return -1
    else:
        return transform_float(val)


def transform_active(val: str) -> bool:
    _, active = val.split(":")
    return active.lower() == "active"


def transform_open(val: str) -> bool:
    is_open, _ = val.split(":")
    return is_open.lower() == "open"


def transform_job_id(val: str) -> str:
    parts = val.split("[")
    job_id = parts[0]
    return job_id


def transform_task_id(val: str) -> Optional[str]:
    parts = val.split("[")
    if len(parts) > 1:
        second_part = parts[1].split("]")
        task_id = second_part[0]
        return task_id
    return None


def transform_tag(val: str) -> Optional[str]:
    parsed = val.strip()
    if parsed == '-':
        return None
    else:
        return parsed
