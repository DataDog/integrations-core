# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any  # noqa: F401

import pytest


@pytest.fixture(scope="function")
def clean_environment():
    os.environ["GOFIPS"] = "0"
    os.environ["OPENSSL_CONF"] = ""
    os.environ["OPENSSL_MODULES"] = ""
    yield


def test_ssl_md5_before_fips(clean_environment):
    import ssl

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.set_ciphers("MD5")
    assert True


def test_cryptography_md5_before_fips(clean_environment):
    from cryptography.hazmat.primitives import hashes

    hashes.Hash(hashes.MD5())
    assert True
