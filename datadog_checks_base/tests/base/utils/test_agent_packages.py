# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from importlib.metadata import distributions

from datadog_checks.base.utils.agent.packages import get_datadog_wheels


def test_get_datadog_wheels():
    # Debug: print all datadog-related packages discovered by importlib.metadata
    print("\n=== DEBUG: Packages discovered by importlib.metadata ===")
    for d in distributions():
        name = d.metadata["Name"]
        if "datadog" in name.lower():
            print(f"  {name}: {d._path}")
    print("=== END DEBUG ===\n")

    packages = get_datadog_wheels()
    print(f"get_datadog_wheels() returned: {packages}")

    # At minimum, checks_base should always be present since we're running tests from it
    assert "checks_base" in packages

    # Verify the result is a sorted list in reverse order (as per function implementation)
    assert packages == sorted(packages, reverse=True)

    # Verify all package names have underscores (dashes should be converted)
    for pkg in packages:
        assert "-" not in pkg
