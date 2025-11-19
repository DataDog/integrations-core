# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.format import json


def test_encode_str():
    obj = {'b': 2, 'a': 1}
    encoded = json.encode(obj)
    assert encoded == '{"b":2,"a":1}'
    decoded = json.decode(encoded)
    assert obj == decoded


def test_encode_bytes():
    obj = {'b': 2, 'a': 1}
    encoded = json.encode_bytes(obj)
    assert encoded == b'{"b":2,"a":1}'
    decoded = json.decode(encoded)
    assert obj == decoded


def test_sort_keys():
    obj = {'b': 2, 'a': 1}
    encoded = json.encode(obj, sort_keys=True)
    assert encoded == '{"a":1,"b":2}'
