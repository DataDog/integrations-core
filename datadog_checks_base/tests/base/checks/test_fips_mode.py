# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os
from typing import Any  # noqa: F401

import mock
import pytest

from datadog_checks.base import AgentCheck
from pathlib import Path
import _hashlib

PATH_TO_EMBEDDED = str(Path(__file__).resolve().parent.parent.parent / "fixtures" / "fips" / "embedded")


@pytest.fixture(scope="function")
def clean_environment():
    AgentCheck().disable_openssl_fips()
    yield


def test_openssl_default_non_fips():
    assert not _hashlib.get_fips_mode()


def test_openssl_fips_enable():
    AgentCheck().enable_openssl_fips(path_to_embedded=PATH_TO_EMBEDDED)
    assert _hashlib.get_fips_mode()


def test_openssl_fips_disable():
    AgentCheck().disable_openssl_fips()
    assert not _hashlib.get_fips_mode()


def test_md5_before_fips():
    import ssl

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.set_ciphers("MD5")
    assert True


def test_md5_after_fips(clean_environment):
    import ssl

    AgentCheck().enable_openssl_fips(path_to_embedded=PATH_TO_EMBEDDED)
    with pytest.raises(ssl.SSLError, match='No cipher can be selected.'):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.set_ciphers("MD5")


def test_cryptography_fips_enable():
    from cryptography.exceptions import InternalError
    from cryptography.hazmat.primitives import hashes

    AgentCheck().enable_cryptography_fips(path_to_embedded=PATH_TO_EMBEDDED)
    with pytest.raises(InternalError, match='Unknown OpenSSL error.'):
        hashes.Hash(hashes.MD5())

