# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock


def test_get_agent_tags():
    with mock.patch('datadog_checks.dev.tooling.git.git_tag_list') as tag_lst:
        from datadog_checks.dev.tooling.commands.agent.common import get_agent_tags

        tag_lst.return_value = ['1.2.3', '4.5.6', '7.8.9']

        assert get_agent_tags(since='1.0.0', to='5.0.0') == ['4.5.6', '1.2.3']
        assert get_agent_tags(since='4.5.6', to='5.0.0') == ['4.5.6']
        assert get_agent_tags(since='4.5.6', to='8.0.0') == ['7.8.9', '4.5.6']
        assert get_agent_tags(since='1.0.0', to=None) == ['7.8.9', '4.5.6', '1.2.3']
        assert get_agent_tags(since='8.0.0', to=None) == []
