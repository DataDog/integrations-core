# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

import os
import pytest

from datadog_checks.base.utils.fips import enable_fips

PATH_TO_OPENSSL_CONF = os.getenv("PATH_TO_OPENSSL_CONF")
PATH_TO_OPENSSL_MODULES = os.getenv("PATH_TO_OPENSSL_MODULES")


@pytest.fixture(scope="function")
def clean_environment(monkeypatch):
    monkeypatch.setenv("GOFIPS", "0")
    monkeypatch.setenv("OPENSSL_CONF", "")
    monkeypatch.setenv("OPENSSL_MODULES", "")
    yield


@pytest.mark.fips_off
def test_ssl_md5_before_fips(clean_environment):
    """
    MD5 cipher should be available through ssl before enabling FIPS mode.
    """
    import ssl

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.set_ciphers("MD5")
    assert True


@pytest.mark.fips_off
def test_cryptography_md5_before_fips(clean_environment):
    """
    MD5 cipher should be available through cryptography before enabling FIPS mode.
    """
    from cryptography.hazmat.primitives import hashes

    assert hashes.Hash(hashes.MD5())


@pytest.mark.fips_on
def test_ssl_md5_after_fips(clean_environment):
    """
    MD5 cipher should not be available through ssl after enabling FIPS mode.
    """
    import ssl

    enable_fips(path_to_openssl_conf=PATH_TO_OPENSSL_CONF, path_to_openssl_modules=PATH_TO_OPENSSL_MODULES)
    with pytest.raises(ssl.SSLError, match='No cipher can be selected.'):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.set_ciphers("MD5")


@pytest.mark.fips_on
def test_cryptography_md5_after_fips(clean_environment):
    """
    MD5 cipher should not be available through cryptography after enabling FIPS mode.
    """
    from cryptography.exceptions import InternalError
    from cryptography.hazmat.primitives import hashes

    enable_fips(path_to_openssl_conf=PATH_TO_OPENSSL_CONF, path_to_openssl_modules=PATH_TO_OPENSSL_MODULES)
    with pytest.raises(InternalError, match='Unknown OpenSSL error.'):
        hashes.Hash(hashes.MD5())
