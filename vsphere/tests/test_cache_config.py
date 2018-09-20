# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.vsphere.cache_config import CacheConfig


def test___init__():
    c = CacheConfig()
    for t in (CacheConfig.Morlist, CacheConfig.Metadata):
        for label in ('last', 'intl'):
            assert len(c._config[t][label]) == 0
    assert c.get_last


def test__check_type():
    c = CacheConfig()
    with pytest.raises(TypeError):
        c._check_type(-99)
    c._check_type(CacheConfig.Morlist)
    c._check_type(CacheConfig.Metadata)


def test_clear():
    c = CacheConfig()
    c.set_interval(CacheConfig.Morlist, 'foo', -99)
    c.clear()
    assert c.get_interval(CacheConfig.Morlist, 'foo') is None


def test_get_set_last():
    c = CacheConfig()
    c.set_last(CacheConfig.Morlist, 'foo', -99)
    assert c._config[CacheConfig.Morlist]['last']['foo'] == -99
    assert c.get_last(CacheConfig.Morlist, 'foo') == -99


def test_get_set_interval():
    c = CacheConfig()
    c.set_interval(CacheConfig.Morlist, 'foo', -99)
    assert c._config[CacheConfig.Morlist]['intl']['foo'] == -99
    assert c.get_interval(CacheConfig.Morlist, 'foo') == -99
