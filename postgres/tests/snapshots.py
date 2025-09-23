# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import decimal
import os
from enum import Enum
from ipaddress import IPv4Address

import orjson

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.common import MetricStub


class SnapshotFileType(Enum):
    REQUESTS = "requests"
    EXPECTED = "expected"
    OUTPUT = "output"


def snapshot_file_path(file_type: SnapshotFileType):
    snapshots_dir = os.path.join(os.path.dirname(__file__), "snapshots")

    test_env = os.environ.get("HATCH_ENV_ACTIVE")
    # typical format of PYTEST_CURRENT_TEST is tests/test_snapshot.py::test_snapshots (call)
    # we want to format to test_snapshot.test_snapshots
    active_test = '.'.join(
        os.environ.get("PYTEST_CURRENT_TEST").split(" ")[0].replace("tests/", "").replace(".py", "").split("::")
    )
    file_prefix = f"{test_env}.{active_test}"

    return os.path.join(snapshots_dir, f"{file_prefix}.{file_type.value}.json")


def read_file(path: str, decode_json: bool = True):
    with open(path, "r") as f:
        if decode_json:
            return orjson.loads(f.read())
        return f.read()


def write_file(content, path: str):
    with open(path, "w") as f:
        f.write(orjson.dumps(content, default=default, option=orjson.OPT_INDENT_2).decode("utf-8"))


def serialize_aggregator(aggregator: AggregatorStub):
    return {
        "metrics": {name: [default(m) for m in list(aggregator.metrics(name))] for name in aggregator.metric_names},
        "events": aggregator.events,
    }


def default(obj):
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    if isinstance(obj, IPv4Address):
        return str(obj)
    if isinstance(obj, MetricStub):
        return {
            "name": obj.name,
            "type": obj.type,
            # The operation time is wall time of the running integration so will vary each time
            "value": obj.value if obj.name != "dd.postgres.operation.time" else 1,
            "tags": sorted(obj.tags),
            "hostname": obj.hostname,
            "device": obj.device,
            "flush_first_value": obj.flush_first_value,
        }
    raise TypeError
