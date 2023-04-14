# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import shutil
import sys

import pytest
from click.testing import CliRunner

from datadog_checks.dev import run_command

# E501: line too long (XXX > 120 characters)
# ruff: noqa: E501
HEADER = "metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric"


@pytest.mark.parametrize(
    'code,output,metric_lines',
    [
        (
            0,
            "Validated!",
            ["my_check.broker_offset,gauge,,offset,,Current message offset on broker.,0,my_check,broker offset,"],
        ),
        (
            1,
            "my_check:2 integration: `check` should be: my_check",
            ["my_check.broker_offset,gauge,,offset,,Current message offset on broker.,0,check,broker offset,"],
        ),
        (
            1,
            "my_check: `check` appears 1 time(s) and does not match metric_prefix defined in the manifest.",
            ["check.broker_offset,gauge,,offset,,Current message offset on broker.,0,my_check,broker offset,"],
        ),
        (
            1,
            "my_check:2 `unknown` is an invalid metric_type.",
            ["my_check.broker_offset,unknown,,offset,,Current message offset on broker.,0,my_check,broker offset,"],
        ),
        (
            1,
            "my_check:2 `2` is an invalid orientation.",
            ["my_check.broker_offset,gauge,,offset,,Current message offset on broker.,2,my_check,broker offset,"],
        ),
        (
            1,
            "my_check:3 `my_check.broker_offset` is a duplicate metric_name",
            [
                "my_check.broker_offset,gauge,,offset,,Current message offset on broker.,0,my_check,broker offset,",
                "my_check.broker_offset,gauge,,offset,,Current message offset on broker.,0,my_check,broker offset,",
            ],
        ),
    ],
)
def test_validate_invalid_metadata_file(code, output, metric_lines):
    with CliRunner().isolated_filesystem():
        shutil.copytree(os.path.dirname(os.path.realpath(__file__)) + "/data/my_check", "./my_check")

        with open("./my_check/metadata.csv", "w") as metadata_file:
            metadata_file.write(HEADER + "\n")
            metadata_file.write("\n".join(metric_lines))

        result = run_command(
            [sys.executable, "-m", "datadog_checks.dev", "--here", "validate", "metadata", "my_check"],
            capture=True,
        )

        assert result.code == code
        assert output in result.stdout, result.stdout
