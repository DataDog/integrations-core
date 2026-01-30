# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.base.utils.tagging import TagsSet


class TestTagsSet:
    """Test the TagsSet data structure with minimal, focused tests."""

    def test_init_empty(self):
        """Test empty initialization."""
        tags = TagsSet()
        assert tags.get_tags() == []

    def test_add_single_tag(self):
        """Test adding a single tag."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        assert tags.get_tags() == ['env:prod']

    def test_add_multiple_values_same_key(self):
        """Test adding multiple values to same key."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        tags.add_tag('env', 'dev')
        assert tags.get_tags() == ['env:dev', 'env:prod']

    def test_add_different_keys(self):
        """Test adding tags with different keys."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        tags.add_tag('app', 'web')
        assert tags.get_tags() == ['app:web', 'env:prod']

    def test_add_unique_tag_replaces(self):
        """Test add_unique_tag replaces existing values."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        tags.add_tag('env', 'dev')
        tags.add_unique_tag('env', 'test')
        assert tags.get_tags() == ['env:test']

    def test_add_unique_tag_new_key(self):
        """Test add_unique_tag with new key."""
        tags = TagsSet()
        tags.add_unique_tag('env', 'prod')
        assert tags.get_tags() == ['env:prod']

    def test_get_tag_empty(self):
        """Test get_tag on empty set."""
        tags = TagsSet()
        assert tags.get_tag('env') == set()

    def test_get_tag_single_value(self):
        """Test get_tag with single value."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        assert tags.get_tag('env') == {'prod'}

    def test_get_tag_multiple_values(self):
        """Test get_tag with multiple values."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        tags.add_tag('env', 'dev')
        assert tags.get_tag('env') == {'prod', 'dev'}

    def test_get_tag_nonexistent_key(self):
        """Test get_tag with non-existent key."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        assert tags.get_tag('app') == set()

    def test_get_tags_unsorted(self):
        """Test get_tags with sort=False."""
        tags = TagsSet()
        tags.add_tag('b', '1')
        tags.add_tag('a', '2')
        result = tags.get_tags(sort=False)
        assert set(result) == {'a:2', 'b:1'}

    def test_get_tags_sorted(self):
        """Test get_tags with sort=True."""
        tags = TagsSet()
        tags.add_tag('b', '1')
        tags.add_tag('a', '2')
        assert tags.get_tags(sort=True) == ['a:2', 'b:1']

    def test_remove_tag_all_values(self):
        """Test removing all values for a key."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        tags.add_tag('env', 'dev')
        tags.remove_tag('env')
        assert tags.get_tags() == []

    def test_remove_tag_specific_value(self):
        """Test removing specific value."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        tags.add_tag('env', 'dev')
        tags.remove_tag('env', 'dev')
        assert tags.get_tags() == ['env:prod']

    def test_remove_tag_nonexistent_key(self):
        """Test removing non-existent key doesn't error."""
        tags = TagsSet()
        tags.remove_tag('env')  # Should not raise
        assert tags.get_tags() == []

    def test_remove_tag_nonexistent_value(self):
        """Test removing non-existent value doesn't error."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        tags.remove_tag('env', 'dev')  # Should not raise
        assert tags.get_tags() == ['env:prod']

    def test_clear_with_tags(self):
        """Test clear removes all tags."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        tags.add_tag('app', 'web')
        tags.clear()
        assert tags.get_tags() == []

    def test_iterator_empty(self):
        """Test iteration on empty set."""
        tags = TagsSet()
        assert list(tags) == []

    def test_iterator_multiple_tags(self):
        """Test iteration yields tuples."""
        tags = TagsSet()
        tags.add_tag('env', 'prod')
        tags.add_tag('app', 'web')
        assert list(tags) == [('app', 'web'), ('env', 'prod')]

    def test_empty_key_raises_error(self):
        """Test that empty key raises ValueError."""
        tags = TagsSet()
        with pytest.raises(ValueError, match="Tag key cannot be empty"):
            tags.add_tag('', 'value')

    def test_empty_key_add_unique_raises_error(self):
        """Test that empty key in add_unique_tag raises ValueError."""
        tags = TagsSet()
        with pytest.raises(ValueError, match="Tag key cannot be empty"):
            tags.add_unique_tag('', 'value')

    def test_special_chars_colon(self):
        """Test key/value with colons."""
        tags = TagsSet()
        tags.add_tag('url', 'http://example.com')
        assert tags.get_tags() == ['url:http://example.com']

    def test_sorting_by_key_then_value(self):
        """Test sorting is by key first, then value."""
        tags = TagsSet()
        tags.add_tag('a', '2')
        tags.add_tag('a', '1')
        tags.add_tag('b', '1')
        assert tags.get_tags() == ['a:1', 'a:2', 'b:1']

    # Tests for both tag formats (key:value and standalone value)
    def test_add_standalone_tag(self):
        """Test adding standalone value tags."""
        tags = TagsSet()
        tags.add_standalone_tag('production')
        tags.add_standalone_tag('critical')
        assert sorted(tags.get_tags()) == ['critical', 'production']

    def test_standalone_tags_use_empty_key(self):
        """Test that standalone tags are stored with empty key."""
        tags = TagsSet()
        tags.add_standalone_tag('production')
        tags.add_standalone_tag('staging')
        # Verify they're stored under empty key
        assert tags.get_standalone_tags() == {'production', 'staging'}

        tags.add_tag('env', 'prod')
        tags.add_tag('env', 'staging')
        # Verify they appear as standalone in output
        assert sorted(tags.get_tags()) == ['env:prod', 'env:staging', 'production', 'staging']
