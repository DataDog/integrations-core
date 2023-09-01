# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import shutil
import sys

from click.testing import CliRunner

from datadog_checks.dev import run_command

TEST_MIB = "A3COM-HUAWEI-LswTRAP-MIB"


def test__traps_db_generation_expanded():
    with CliRunner().isolated_filesystem():
        shutil.copytree(f"{os.path.dirname(os.path.realpath(__file__))}/data", "./data")

        result = run_command(
            [
                sys.executable,
                "-m",
                "datadog_checks.dev",
                "meta",
                "snmp",
                "generate-traps-db",
                "-o",
                "./data/",
                f"./data/{TEST_MIB}",
                "--output-format",
                "json",
            ],
            capture=True,
        )

        assert 0 == result.code
        assert "Wrote trap data to" in result.stdout

        with open(f"./data/{TEST_MIB}.json", "r") as trap_db_file:
            trap_db = json.load(trap_db_file)

        with open("./data/expected_expanded.json", "r") as expected_file:
            expected = json.load(expected_file)

        assert trap_db == expected


def test__traps_db_generation_compact():
    with CliRunner().isolated_filesystem():
        shutil.copytree(f"{os.path.dirname(os.path.realpath(__file__))}/data", "./data")

        result = run_command(
            [
                sys.executable,
                "-m",
                "datadog_checks.dev",
                "meta",
                "snmp",
                "generate-traps-db",
                "--output-file",
                "./data/output.json",
                f"./data/{TEST_MIB}",
                "--output-format",
                "json",
            ],
            capture=True,
        )

        assert 0 == result.code
        assert "Wrote trap data to" in result.stdout

        with open("./data/output.json", "r") as trap_db_file:
            trap_db = json.load(trap_db_file)

        with open("./data/expected_compact.json", "r") as expected_file:
            expected = json.load(expected_file)

        assert trap_db == expected
