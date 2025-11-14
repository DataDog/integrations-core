# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from typing import Optional


def is_affirmative(val: str) -> bool:
    return "yes" in val.lower()


def transform_status(status: str) -> int:
    return int(status == "ok")


def transform_float(val: str) -> float:
    val = val.strip()
    if val == "-":
        return -1
    else:
        # Remove units from end of strings
        # sometimes there are trailing Ls to represent a limit reached
        # ie: 22.00% L
        float_val = re.sub(r'\D+$', '', val)
        return float(float_val)


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


def transform_error(val: str) -> bool:
    parsed = val.strip()
    return not parsed == '-'


def transform_time_left(val: str) -> int:
    val = val.strip().rstrip("L")
    if val in ("-", "UNLIMITED"):
        return -1

    # time_left looks like 1:48 L where there are hours and minutes
    # we will convert to seconds
    parts = val.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 3600 + int(parts[1]) * 60
    else:
        return int(val) * 60
