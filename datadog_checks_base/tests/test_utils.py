# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.utils.common import pattern_filter, pattern_filter_chain


class Item:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self.name == other.name


class TestPatternFilter:
    def test_no_items(self):
        items = []
        patterns = ['mock']

        assert pattern_filter(items, patterns) == []

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
        items = [Item('abc'), Item('def'), Item('abcdef'), Item('ghi')]
        patterns = ['abc', 'def']

        assert pattern_filter(items, patterns, key=lambda item: item.name) == [
            Item('abc'), Item('def'), Item('abcdef')
        ]


class TestPatternFilterChain:
    def test_no_items(self):
        items = []
        whitelist = ['mock']

        assert pattern_filter_chain(items, whitelist=whitelist) == []

    def test_no_patterns(self):
        items = ['mock']

        assert pattern_filter_chain(items) is items

    def test_multiple_matches_whitelist(self):
        items = ['abc', 'def', 'abcdef', 'ghi']
        whitelist = ['abc', 'def']

        assert pattern_filter_chain(items, whitelist=whitelist) == ['abc', 'def', 'abcdef']

    def test_multiple_matches_blacklist(self):
        items = ['abc', 'def', 'abcdef', 'ghi']
        blacklist = ['abc', 'def']

        assert pattern_filter_chain(items, blacklist=blacklist) == ['ghi']

    def test_whitelist_override(self):
        items = ['abc', 'def', 'abcdef', 'ghi']
        whitelist = ['def']
        blacklist = ['abc', 'def']

        assert pattern_filter_chain(items, whitelist=whitelist, blacklist=blacklist) == ['def', 'abcdef', 'ghi']

    def test_key_function(self):
        items = [Item('abc'), Item('def'), Item('abcdef'), Item('ghi')]
        whitelist = ['abc', 'def']

        assert pattern_filter_chain(items, whitelist=whitelist, key=lambda item: item.name) == [
            Item('abc'), Item('def'), Item('abcdef')
        ]
