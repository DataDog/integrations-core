# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.env import serialize_data, deserialize_data


@pytest.mark.unit
def test_serialize_data():
    data = {"test": "test"}
    serialized = serialize_data(data)
    assert deserialize_data(serialized) == data

def test_serialize_data_large():
    data = {"test": "test" * 10000}
    serialized = serialize_data(data)
    assert deserialize_data(serialized) == data