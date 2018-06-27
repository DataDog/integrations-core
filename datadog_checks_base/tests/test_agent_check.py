# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.checks import AgentCheck


def test_instance():
    """
    Simply assert the class can be insantiated
    """
    AgentCheck()


class TestTags:
    def test_default_string(self):
        check = AgentCheck()
        tag = 'default:string'
        tags = [tag]

        normalized_tags = check._normalize_tags(tags, None)
        normalized_tag = normalized_tags[0]

        assert normalized_tags is not tags
        assert normalized_tag == tag.encode('utf-8')

    def test_bytes_string(self):
        check = AgentCheck()
        tag = b'bytes:string'
        tags = [tag]

        normalized_tags = check._normalize_tags(tags, None)
        normalized_tag = normalized_tags[0]

        assert normalized_tags is not tags
        # Ensure no new allocation occurs
        assert normalized_tag is tag

    def test_unicode_string(self):
        check = AgentCheck()
        tag = u'unicode:string'
        tags = [tag]

        normalized_tags = check._normalize_tags(tags, None)
        normalized_tag = normalized_tags[0]

        assert normalized_tags is not tags
        assert normalized_tag == tag.encode('utf-8')
