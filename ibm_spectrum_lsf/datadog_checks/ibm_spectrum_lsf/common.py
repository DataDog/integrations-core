# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import string


def is_affirmative(val):
    return "yes" in val.lower()


def transform_status(status):
    return int(status == "ok")


def transform_float(val):
    if val == "-":
        return -1
    else:
        val = val.rstrip(string.ascii_letters + string.punctuation)
        return float(val)


def transform_runtime(val):
    if val == "UNLIMITED":
        return -1
    else:
        return transform_float(val)


def transform_active(val):
    _, active = val.split(":")
    return active.lower() == "Active"


def transform_open(val):
    is_open, _ = val.split(":")
    return is_open.lower() == "Open"


def transform_job_id(val):
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


def transform_tag(val):
    parsed = val.strip()
    if parsed == '-':
        return None
    else:
        return parsed
