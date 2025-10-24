# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest


def test_ddtrace_version():
    """Verify ddtrace version for this test run"""
    try:
        import ddtrace

        version = ddtrace.__version__
        print(f"\n{'=' * 60}")
        print(f"DDTRACE VERSION: {version}")
        print(f"{'=' * 60}\n")
        # Assert the expected version contains MAJOR.MINOR (3.17)
        # Since this is a dev version, we only check for the major.minor portion
        expected_major_minor = "3.17"
        assert expected_major_minor in version, (
            f"Expected ddtrace version to contain {expected_major_minor}, got {version}"
        )
    except ImportError:
        pytest.fail("ddtrace is not installed")
