# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from ddev.cli.size.diff import calculate_diff
from ddev.cli.size.utils.common_funcs import convert_to_human_readable_size


def to_native_path(path: str) -> str:
    return path.replace("/", os.sep)


def test_calculate_diff():
    size_before = [
        {
            "Name": "foo",
            "Version": "1.0.0",
            "Size_Bytes": 1000,
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
        {
            "Name": "bar",
            "Version": "2.0.0",
            "Size_Bytes": 2000,
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
        {
            "Name": "deleted",
            "Version": "3.0.0",
            "Size_Bytes": 1500,
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
    ]

    size_after = [
        {
            "Name": "foo",
            "Version": "1.1.0",
            "Size_Bytes": 1200,
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
        {
            "Name": "bar",
            "Version": "2.0.0",
            "Size_Bytes": 2000,
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
        {
            "Name": "new",
            "Version": "0.1.0",
            "Size_Bytes": 800,
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
        },
    ]

    result, _, _, _ = calculate_diff(size_before, size_after, "linux-aarch64", "3.12")

    expected = [
        {
            "Name": "bar",
            "Version": "2.0.0",
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
            "Size_Bytes": 0,
            "Size": convert_to_human_readable_size(0),
            "Percentage": 0.0,
            "Delta_Type": "Unchanged",
        },
        {
            "Name": "deleted",
            "Version": "3.0.0",
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
            "Size_Bytes": -1500,
            "Size": convert_to_human_readable_size(-1500),
            "Percentage": -100.0,
            "Delta_Type": "Removed",
        },
        {
            "Name": "foo",
            "Version": "1.0.0 -> 1.1.0",
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
            "Size_Bytes": 200,
            "Size": convert_to_human_readable_size(200),
            "Percentage": 20.0,
            "Delta_Type": "Modified",
        },
        {
            "Name": "new",
            "Version": "0.1.0",
            "Type": "Integration",
            "Platform": "linux-aarch64",
            "Python_Version": "3.12",
            "Size_Bytes": 800,
            "Size": convert_to_human_readable_size(800),
            "Percentage": 0.0,
            "Delta_Type": "New",
        },
    ]

    assert sorted(result, key=lambda x: x["Name"]) == sorted(expected, key=lambda x: x["Name"])
