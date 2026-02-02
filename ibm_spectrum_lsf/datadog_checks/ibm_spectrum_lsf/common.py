# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

FLOAT_PATTERN = re.compile(r"\D+$")


def is_affirmative(val: str) -> bool:
    return "yes" in val.lower()


def transform_status(status: str) -> int:
    return 1 if status.lower() == "ok" else 0


def transform_float(val: str) -> float:
    # Remove units from end of strings
    # sometimes there are trailing Ls to represent a limit reached
    # ie: 22.00% L
    # If the value passed is "-", return -1
    return -1 if val.strip() == "-" else float(FLOAT_PATTERN.sub('', val))


def transform_runtime(val: str) -> float:
    return -1 if val.strip() == "UNLIMITED" else transform_float(val)


def transform_active(val: str) -> bool:
    return val.split(":")[-1].lower() == "active"


def transform_open(val: str) -> bool:
    return val.split(":")[0].lower() == "open"


def transform_job_id(val: str) -> str:
    return val.split("[")[0]


def transform_tag(val: str) -> str | None:
    parsed = val.strip()
    if parsed == '-':
        return None
    else:
        return parsed


def transform_job_with_task(val):
    parts = val.split("[")
    job_id = parts[0]
    return job_id


def transform_task_id(val):
    parts = val.split("[")
    if len(parts) > 1:
        second_part = parts[1].split("]")
        task_id = second_part[0]
        return task_id
    return None


def transform_job_name(val):
    parts = val.split("[")
    if len(parts) > 1:
        job_name = parts[0]
        return job_name
    return transform_tag(val)


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
