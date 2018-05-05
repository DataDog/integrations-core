# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.utils.common import pattern_filter


class TestPatternFilter:
    def test_no_patterns(self):
        items = ['mock']
        patterns = []

        assert pattern_filter(items, patterns) is items

    def test_multiple_matches_whitelist(self):
        items = ['abc', 'def', 'abcdef', 'ghi']
        patterns = ['abc', 'def']

        assert pattern_filter(items, patterns) == ['abc', 'def', 'abcdef']

    def test_multiple_matches_blacklist(self):
        items = ['abc', 'def', 'abcdef', 'ghi']
        patterns = ['abc', 'def']

        assert pattern_filter(items, patterns, exclude=True) == ['ghi']

    def test_key_function(self):
        class Item:
            def __init__(self, name):
                self.name = name

            def __eq__(self, other):
                return self.name == other.name

        items = [Item('abc'), Item('def'), Item('abcdef'), Item('ghi')]
        patterns = ['abc', 'def']

        assert pattern_filter(items, patterns, key=lambda item: item.name) == [
            Item('abc'), Item('def'), Item('abcdef')
        ]
