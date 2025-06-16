# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from ddev.cli.size.diff import get_diff
from ddev.cli.size.utils.common_funcs import convert_to_human_readable_size


def to_native_path(path: str) -> str:
    return path.replace("/", os.sep)


def test_get_diff():
    size_before = [
        {"Name": "foo", "Version": "1.0.0", "Size_Bytes": 1000, "Type": "Integration"},
        {"Name": "bar", "Version": "2.0.0", "Size_Bytes": 2000, "Type": "Integration"},
        {"Name": "deleted", "Version": "3.0.0", "Size_Bytes": 1500, "Type": "Integration"},
    ]

    size_after = [
        {"Name": "foo", "Version": "1.1.0", "Size_Bytes": 1200, "Type": "Integration"},
        {"Name": "bar", "Version": "2.0.0", "Size_Bytes": 2000, "Type": "Integration"},
        {"Name": "new", "Version": "0.1.0", "Size_Bytes": 800, "Type": "Integration"},
    ]

    result = get_diff(size_before, size_after, "Integration")

    expected = [
        {
            "Name": "deleted (DELETED)",
            "Version": "3.0.0",
            "Type": "Integration",
            "Size_Bytes": -1500,
            "Size": convert_to_human_readable_size(-1500),
        },
        {
            "Name": "foo",
            "Version": "1.0.0 -> 1.1.0",
            "Type": "Integration",
            "Size_Bytes": 200,
            "Size": convert_to_human_readable_size(200),
        },
        {
            "Name": "new (NEW)",
            "Version": "0.1.0",
            "Type": "Integration",
            "Size_Bytes": 800,
            "Size": convert_to_human_readable_size(800),
        },
    ]

    assert sorted(result, key=lambda x: x["Name"]) == expected
