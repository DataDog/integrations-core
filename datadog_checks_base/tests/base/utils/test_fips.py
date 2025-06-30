# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys

import pytest

from datadog_checks.base.utils.fips import is_enabled


@pytest.fixture
def set_fips_registry(request):
    import winreg

    winreg.SetValue(
        winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Lsa\FipsAlgorithmPolicy", winreg.REG_SZ, "Enabled"
    )


@pytest.fixture
def set_non_fips_registry(request):
    import winreg

    winreg.SetValue(
        winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control\Lsa\FipsAlgorithmPolicy",
        winreg.REG_SZ,
        "Disabled",
    )


@pytest.mark.parametrize("gofips_value,is_fips", [("0", False), ("1", True)])
@pytest.mark.skipif(sys.platform == "win32", reason="Testing only on Linux")
def test_fips_status_linux(monkeypatch, gofips_value, is_fips):
    monkeypatch.setenv("GOFIPS", gofips_value)
    assert is_enabled() == is_fips


@pytest.mark.skipif(sys.platform != "win32", reason="Testing only on Windows")
def test_fips_is_enabled_windows(set_fips_registry):
    assert is_enabled()


@pytest.mark.skipif(sys.platform != "win32", reason="Testing only on Windows")
def test_fips_is_disabled_windows(set_non_fips_registry):
    assert not is_enabled()
