# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

import mock
import pytest
from mock import MagicMock, patch
from pyVmomi import vim
from six import iteritems

from datadog_checks.vsphere.api_rest import VSphereRestAPI
from datadog_checks.vsphere.cache import InfrastructureCache, MetricsMetadataCache, TagsCache, VSphereCache
from datadog_checks.vsphere.config import VSphereConfig
from datadog_checks.vsphere.constants import ALL_RESOURCES_WITH_METRICS

logger = logging.getLogger()


def test_generic_cache_usage():
    interval = 120
    with patch('datadog_checks.vsphere.cache.time') as time:
        mocked_timestamp = object()
        time.time = MagicMock(return_value=mocked_timestamp)
        cache = VSphereCache(interval)
        # Assert initialization
        assert cache._last_ts == 0
        assert cache._interval == interval
        assert not cache._content

        # Update the content
        with cache.update():
            assert cache._last_ts == 0
            cache._content['foo'] = 'bar'

        # Assert that the cache last ts was updated successfully
        assert cache._last_ts is mocked_timestamp

        # Update the content but an error is raised
        with pytest.raises(Exception), cache.update():
            assert not cache._content
            cache._content['foo'] = 'baz'
            raise Exception('foo')

        # Because of the exception the content and the timestamps were not updated
        assert cache._last_ts is mocked_timestamp
        assert cache._content['foo'] == 'bar'


def test_refresh():
    interval = 120
    with patch('datadog_checks.vsphere.cache.time') as time:
        base_time = 1576263848
        mocked_timestamps = [base_time + 50 * i for i in range(4)]
        time.time = MagicMock(side_effect=mocked_timestamps)
        cache = VSphereCache(interval)

        assert cache.is_expired()
        cache._last_ts = base_time

        assert not cache.is_expired()  # Only 50 seconds
        assert not cache.is_expired()  # Only 100 seconds
        assert cache.is_expired()  # 150 > 120 seconds


def test_metrics_metadata_cache():
    cache = MetricsMetadataCache(float('inf'))
    data = {k: object() for k in ALL_RESOURCES_WITH_METRICS}

    with cache.update():
        for k, v in iteritems(data):
            cache.set_metadata(k, v)

    for k, v in iteritems(data):
        assert cache.get_metadata(k) == v


@pytest.mark.usefixtures("mock_type")
def test_infrastructure_cache():
    cache = InfrastructureCache(float('inf'))
    mors = {MagicMock(spec=k): object() for k in ALL_RESOURCES_WITH_METRICS * 2}
    with cache.update():
        for k, v in iteritems(mors):
            cache.set_mor_data(k, v)

    for r in ALL_RESOURCES_WITH_METRICS:
        assert len(list(cache.get_mors(r))) == 2

    for k, v in iteritems(mors):
        assert cache.get_mor_props(k) == v


@pytest.mark.usefixtures("mock_type", "mock_rest_api")
def test_tags_cache(realtime_instance):
    cache = TagsCache(float('inf'))
    config = VSphereConfig(realtime_instance, logger)
    mock_api = VSphereRestAPI(config, log=logger)
    mock_mors = [mock.MagicMock(spec=vim.VirtualMachine, _moId="foo")]

    with cache.update():
        cache.set_all_tags(mock_api.get_resource_tags_for_mors(mock_mors))

    vm_mor = vim.VirtualMachine(moId='VM4-4-1')
    vm2_mor = vim.VirtualMachine(moId='i-dont-have-tags')
    datastore = vim.Datastore(moId='NFS-Share-1')

    assert cache.get_mor_tags(vm_mor) == ['my_cat_name_1:my_tag_name_1', 'my_cat_name_2:my_tag_name_2']
    assert cache.get_mor_tags(datastore) == ['my_cat_name_2:my_tag_name_2']
    assert cache.get_mor_tags(vm2_mor) == []
