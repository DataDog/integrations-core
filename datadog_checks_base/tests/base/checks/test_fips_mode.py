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
from cryptography.hazmat.backends import default_backend


def test_cryptography():
    """
    Test that when GOFIPS=1, cryptography enters FIPS mode.
    """
    with mock.patch.dict(os.environ, {'GOFIPS': '1'}):
        import datadog_checks.base

        assert default_backend()._fips_enabled
        assert default_backend()._enable_fips()
