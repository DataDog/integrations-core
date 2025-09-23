# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

serialization = None


@pytest.fixture(autouse=True)
def load_serialization_module(caplog):
    global serialization

    if serialization is None:
        with caplog.at_level(logging.DEBUG):
            from datadog_checks.base.utils import serialization


def test_fast_json():
    assert serialization.json.__name__ == 'orjson'
