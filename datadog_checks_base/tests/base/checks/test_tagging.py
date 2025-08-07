# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.base.utils.tagging import TagsSet


class TestTagsSet:
    """Test the TagsSet data structure."""

    def test_init(self):
        """Test TagsSet initialization."""
        tags_set = TagsSet()
        assert tags_set.get_tags() == []

    def test_add_tag(self):
        """Test adding tags."""
        tags_set = TagsSet()

        # Add single tag
        tags_set.add_tag('env', 'production')
        assert tags_set.get_tags() == [('env', 'production')]

        # Add another value to same key
        tags_set.add_tag('env', 'staging')
        expected = [('env', 'production'), ('env', 'staging')]
        assert sorted(tags_set.get_tags()) == sorted(expected)

        # Add tag with different key
        tags_set.add_tag('service', 'web')
        expected = [('env', 'production'), ('env', 'staging'), ('service', 'web')]
        assert sorted(tags_set.get_tags()) == sorted(expected)

    def test_add_unique_tag(self):
        """Test adding unique tags."""
        tags_set = TagsSet()

        # Add initial tag
        tags_set.add_tag('env', 'production')
        tags_set.add_tag('env', 'staging')
        assert len([t for t in tags_set.get_tags() if t[0] == 'env']) == 2

        # Add unique tag - should replace all existing values for that key
        tags_set.add_unique_tag('env', 'development')
        assert tags_set.get_tags() == [('env', 'development')]

        # Add unique tag for new key
        tags_set.add_unique_tag('region', 'us-east-1')
        expected = [('env', 'development'), ('region', 'us-east-1')]
        assert sorted(tags_set.get_tags()) == sorted(expected)

    def test_get_tag(self):
        """Test getting values for a specific key."""
        tags_set = TagsSet()

        # Test getting from empty set
        assert tags_set.get_tag('env') == set()

        # Add some tags
        tags_set.add_tag('env', 'production')
        tags_set.add_tag('env', 'staging')
        tags_set.add_tag('env', 'development')
        tags_set.add_tag('service', 'web')
        tags_set.add_tag('service', 'api')

        # Test getting existing keys
        assert tags_set.get_tag('env') == {'production', 'staging', 'development'}
        assert tags_set.get_tag('service') == {'web', 'api'}

        # Test getting non-existent key
        assert tags_set.get_tag('region') == set()

        # Test after unique tag (replaces all values)
        tags_set.add_unique_tag('env', 'testing')
        assert tags_set.get_tag('env') == {'testing'}

        # Test after removing specific value
        tags_set.add_tag('env', 'qa')
        tags_set.remove_tag('env', 'testing')
        assert tags_set.get_tag('env') == {'qa'}

        # Test after removing all values for a key
        tags_set.remove_tag('env')
        assert tags_set.get_tag('env') == set()

    def test_iterator(self):
        """Test iteration over tags."""
        tags_set = TagsSet()

        # Add tags
        tags_set.add_tag('env', 'production')
        tags_set.add_tag('service', 'web')
        tags_set.add_tag('region', 'us-east-1')

        # Test iteration
        tags_list = list(tags_set)
        expected = [('env', 'production'), ('region', 'us-east-1'), ('service', 'web')]
        assert tags_list == expected

        # Test that iteration returns sorted results
        tags_via_iter = list(tags_set)
        tags_via_method = tags_set.get_tags(sort=True)
        assert tags_via_iter == tags_via_method

    def test_tags_sorted(self):
        """Test that get_tags() returns sorted results."""
        tags_set = TagsSet()

        # Add tags in non-sorted order
        tags_set.add_tag('zoo', 'animals')
        tags_set.add_tag('apple', 'fruit')
        tags_set.add_tag('banana', 'fruit')
        tags_set.add_tag('apple', 'company')

        # Should be sorted by key first, then value
        expected = [('apple', 'company'), ('apple', 'fruit'), ('banana', 'fruit'), ('zoo', 'animals')]
        assert tags_set.get_tags() == expected
        assert tags_set.get_tags(sort=True) == expected

        # Test unsorted - should still contain all tags but order not guaranteed
        unsorted_tags = tags_set.get_tags(sort=False)
        assert len(unsorted_tags) == len(expected)
        assert set(unsorted_tags) == set(expected)

    def test_remove_tag_all_values(self):
        """Test removing all tags under a key."""
        tags_set = TagsSet()

        # Add multiple tags
        tags_set.add_tag('env', 'production')
        tags_set.add_tag('env', 'staging')
        tags_set.add_tag('env', 'development')
        tags_set.add_tag('service', 'web')

        # Remove all env tags
        tags_set.remove_tag('env')
        assert tags_set.get_tags() == [('service', 'web')]

        # Remove non-existent key (should not raise error)
        tags_set.remove_tag('non_existent')
        assert tags_set.get_tags() == [('service', 'web')]

    def test_remove_tag_specific_value(self):
        """Test removing specific key:value tags."""
        tags_set = TagsSet()

        # Add multiple tags
        tags_set.add_tag('env', 'production')
        tags_set.add_tag('env', 'staging')
        tags_set.add_tag('env', 'development')
        tags_set.add_tag('service', 'web')

        # Remove specific env tag
        tags_set.remove_tag('env', 'staging')
        expected = [('env', 'development'), ('env', 'production'), ('service', 'web')]
        assert sorted(tags_set.get_tags()) == sorted(expected)

        # Remove non-existent value (should not raise error)
        tags_set.remove_tag('env', 'non_existent')
        assert sorted(tags_set.get_tags()) == sorted(expected)

        # Remove last value for a key - key should be removed
        tags_set.remove_tag('service', 'web')
        expected = [('env', 'development'), ('env', 'production')]
        assert sorted(tags_set.get_tags()) == sorted(expected)

    def test_clear(self):
        """Test clearing all tags."""
        tags_set = TagsSet()

        # Add tags
        tags_set.add_tag('env', 'production')
        tags_set.add_tag('service', 'web')
        tags_set.add_tag('region', 'us-east-1')

        assert len(tags_set.get_tags()) > 0

        # Clear all tags
        tags_set.clear()
        assert tags_set.get_tags() == []

    def test_edge_cases(self):
        """Test edge cases."""
        tags_set = TagsSet()

        # Test empty string key and value
        tags_set.add_tag('', '')
        assert tags_set.get_tags() == [('', '')]

        # Test with special characters
        tags_set.clear()
        tags_set.add_tag('key:with:colons', 'value:with:colons')
        tags_set.add_tag('key/with/slashes', 'value/with/slashes')
        tags_set.add_tag('key=with=equals', 'value=with=equals')

        assert len(tags_set.get_tags()) == 3

        # Test removing with special characters
        tags_set.remove_tag('key:with:colons', 'value:with:colons')
        assert len(tags_set.get_tags()) == 2

    def test_multiple_operations(self):
        """Test a sequence of operations."""
        tags_set = TagsSet()

        # Build up tags
        tags_set.add_tag('env', 'prod')
        tags_set.add_tag('env', 'dev')
        tags_set.add_tag('service', 'api')
        tags_set.add_unique_tag('version', '1.0.0')

        # Verify state
        assert len(tags_set.get_tags()) == 4

        # Remove specific tag
        tags_set.remove_tag('env', 'dev')
        assert len(tags_set.get_tags()) == 3

        # Update version
        tags_set.add_unique_tag('version', '2.0.0')
        expected = [('env', 'prod'), ('service', 'api'), ('version', '2.0.0')]
        assert sorted(tags_set.get_tags()) == sorted(expected)

        # Remove all env tags
        tags_set.remove_tag('env')
        expected = [('service', 'api'), ('version', '2.0.0')]
        assert sorted(tags_set.get_tags()) == sorted(expected)

        # Clear everything
        tags_set.clear()
        assert tags_set.get_tags() == []
