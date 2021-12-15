# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.base import stubs
from datadog_checks.base.utils.agent.utils import should_profile_memory


class TestShouldProfileMemory:
    def test_default(self):
        with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', return_value=''):
            assert should_profile_memory(stubs.datadog_agent, 'test') is True

    def test_include_enable(self):
        # Keep a reference for use during mock
        get_config = stubs.datadog_agent.get_config

        def mock_get_config(key):
            if key == 'tracemalloc_include':
                return 'test'

            return get_config(key)

        with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', side_effect=mock_get_config):
            assert should_profile_memory(stubs.datadog_agent, 'test') is True

    def test_include_disable(self):
        # Keep a reference for use during mock
        get_config = stubs.datadog_agent.get_config

        def mock_get_config(key):
            if key == 'tracemalloc_include':
                return 'test1,test2'

            return get_config(key)

        with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', side_effect=mock_get_config):
            assert should_profile_memory(stubs.datadog_agent, 'test') is False

    def test_include_exclude(self):
        # Keep a reference for use during mock
        get_config = stubs.datadog_agent.get_config

        def mock_get_config(key):
            if key == 'tracemalloc_include':
                return 'test'
            elif key == 'tracemalloc_exclude':
                return 'test'

            return get_config(key)

        with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', side_effect=mock_get_config):
            assert should_profile_memory(stubs.datadog_agent, 'test') is False

    def test_whitelist_enable(self):
        # Keep a reference for use during mock
        get_config = stubs.datadog_agent.get_config

        def mock_get_config(key):
            if key == 'tracemalloc_whitelist':
                return 'test'

            return get_config(key)

        with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', side_effect=mock_get_config):
            assert should_profile_memory(stubs.datadog_agent, 'test') is True

    def test_whitelist_disable(self):
        # Keep a reference for use during mock
        get_config = stubs.datadog_agent.get_config

        def mock_get_config(key):
            if key == 'tracemalloc_whitelist':
                return 'test1,test2'

            return get_config(key)

        with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', side_effect=mock_get_config):
            assert should_profile_memory(stubs.datadog_agent, 'test') is False

    def test_whitelist_blacklist(self):
        # Keep a reference for use during mock
        get_config = stubs.datadog_agent.get_config

        def mock_get_config(key):
            if key == 'tracemalloc_whitelist':
                return 'test'
            elif key == 'tracemalloc_blacklist':
                return 'test'

            return get_config(key)

        with mock.patch('datadog_checks.base.stubs.datadog_agent.get_config', side_effect=mock_get_config):
            assert should_profile_memory(stubs.datadog_agent, 'test') is False
