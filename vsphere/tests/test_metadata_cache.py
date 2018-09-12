# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.vsphere.metadata_cache import MetadataCache, MetadataNotFoundError


@pytest.fixture
def cache():
    return MetadataCache()


def test_contains(cache):
    with pytest.raises(KeyError):
        cache.contains("instance", "foo")
    cache._metadata["instance"] = {"foo_id": {}}
    assert cache.contains("instance", "foo_id") is True
    assert cache.contains("instance", "foo") is False


def test_set_metadata(cache):
    cache._metadata["foo_instance"] = {}
    cache.set_metadata("foo_instance", {"foo_id": {}})
    assert "foo_id" in cache._metadata["foo_instance"]


def test_get_metadata(cache):
    with pytest.raises(KeyError):
        cache.get_metadata("instance", "id")

    cache._metadata["foo_instance"] = {
        "foo_id": {"name": "metric_name"}
    }

    assert cache.get_metadata("foo_instance", "foo_id")["name"] == "metric_name"

    with pytest.raises(MetadataNotFoundError):
        cache.get_metadata("foo_instance", "bar_id")
