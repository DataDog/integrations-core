import pytest

from datadog_checks.mysql.tag_manager import TagManager, TagType


class TestTagManager:
    def test_init(self):
        """Test initialization of TagManager"""
        tag_manager = TagManager()
        assert tag_manager._tags == {}
        assert tag_manager._cached_tag_list is None
        assert tag_manager._keyless == TagType.KEYLESS

    def test_set_tag_new_key(self):
        """Test setting a tag for a new key"""
        tag_manager = TagManager()
        tag_manager.set_tag('test_key', 'test_value')
        assert tag_manager._tags == {'test_key': ['test_value']}
        assert tag_manager._cached_tag_list is None

    def test_set_tag_existing_key_append(self):
        """Test appending a value to an existing key"""
        tag_manager = TagManager()
        tag_manager.set_tag('test_key', 'value1')
        tag_manager.set_tag('test_key', 'value2')
        assert tag_manager._tags == {'test_key': ['value1', 'value2']}
        assert tag_manager._cached_tag_list is None

    def test_set_tag_existing_key_replace(self):
        """Test replacing values for an existing key"""
        tag_manager = TagManager()
        tag_manager.set_tag('test_key', 'value1')
        tag_manager.set_tag('test_key', 'value2', replace=True)
        assert tag_manager._tags == {'test_key': ['value2']}
        assert tag_manager._cached_tag_list is None

    def test_set_tag_duplicate_value(self):
        """Test setting a duplicate value for a key"""
        tag_manager = TagManager()
        tag_manager.set_tag('test_key', 'test_value')
        tag_manager.set_tag('test_key', 'test_value')
        assert tag_manager._tags == {'test_key': ['test_value']}
        assert tag_manager._cached_tag_list is None

    def test_delete_tag_nonexistent_key(self):
        tag_manager = TagManager()
        assert not tag_manager.delete_tag('nonexistent_key')

    def test_delete_tag_nonexistent_value(self):
        tag_manager = TagManager()
        tag_manager.set_tag('test_key', 'value1')
        assert not tag_manager.delete_tag('test_key', 'nonexistent_value')

    @pytest.mark.parametrize(
        'key,values,delete_key,delete_value,expected_tags,expected_internal_state,description',
        [
            (
                'test_key',
                ['value1', 'value2'],
                'test_key',
                'value1',
                ['test_key:value2'],
                {'test_key': ['value2']},
                'deleting specific value'
            ),
            (
                'test_key',
                ['value1', 'value2'],
                'test_key',
                None,
                [],
                {},
                'deleting all values for key'
            ),
            (
                None,
                ['value1', 'value2'],
                None,
                'value1',
                ['value2'],
                {TagType.KEYLESS: ['value2']},
                'deleting specific keyless value'
            ),
            (
                None,
                ['value1', 'value2'],
                None,
                None,
                [],
                {},
                'deleting all keyless values'
            ),
        ]
    )
    def test_delete_tag(self, key, values, delete_key, delete_value, expected_tags, expected_internal_state, description):
        """Test various tag deletion scenarios"""
        tag_manager = TagManager()
        # Set up initial tags
        for value in values:
            tag_manager.set_tag(key, value)

        # Generate initial cache
        tag_manager.get_tags()
        assert tag_manager._cached_tag_list is not None

        # Perform deletion
        assert tag_manager.delete_tag(delete_key, delete_value)

        # Verify cache is invalidated immediately after deletion
        assert tag_manager._cached_tag_list is None

        # Verify internal state
        assert tag_manager._tags == expected_internal_state

        # Verify external state (get_tags)
        assert tag_manager.get_tags() == expected_tags

    @pytest.mark.parametrize(
        'initial_tags,tag_list,replace,expected_tags,description',
        [
            ([], ['key1:value1', 'key2:value2', 'value3'], False, ['key1:value1', 'key2:value2', 'value3'], 'setting new tags'),
            (['key1:old_value'], ['key1:new_value'], True, ['key1:new_value'], 'replacing existing tags'),
            (['key1:old_value'], ['key1:new_value'], False, ['key1:new_value', 'key1:old_value'], 'appending to existing tags'),
            ([], ['key1:value1', 'key1:value1'], False, ['key1:value1'], 'setting duplicate values'),
            ([], ['key1:value1', 'value2', 'key2:value3'], False, ['key1:value1', 'key2:value3', 'value2'], 'setting mixed format tags'),
        ]
    )
    def test_set_tags_from_list(self, initial_tags, tag_list, replace, expected_tags, description):
        """Test various tag list setting scenarios"""
        tag_manager = TagManager()
        # Set up initial tags if any
        for tag in initial_tags:
            if ':' in tag:
                key, value = tag.split(':', 1)
                tag_manager.set_tag(key, value)
            else:
                tag_manager.set_tag(None, tag)

        tag_manager.set_tags_from_list(tag_list, replace=replace)
        assert tag_manager.get_tags() == expected_tags

    def test_get_tags_empty(self):
        tag_manager = TagManager()
        assert tag_manager.get_tags() == []

    def test_get_tags(self):
        """Test getting tags with various combinations of key-value and keyless tags"""
        tag_manager = TagManager()
        tag_manager.set_tag('key1', 'value1')
        tag_manager.set_tag('key2', 'value2')
        tag_manager.set_tag(None, 'keyless1')
        tag_manager.set_tag(None, 'keyless2')

        expected = ['key1:value1', 'key2:value2', 'keyless1', 'keyless2']
        assert tag_manager.get_tags() == expected

    def test_get_tags_cache(self):
        """Test that get_tags uses and updates the cache correctly"""
        tag_manager = TagManager()
        tag_manager.set_tag('key1', 'value1')

        # First call should generate cache
        first_result = tag_manager.get_tags()
        assert first_result == ['key1:value1']
        assert tag_manager._cached_tag_list == ['key1:value1']

        # Second call should use cache
        second_result = tag_manager.get_tags()
        assert second_result == ['key1:value1']
        assert tag_manager._cached_tag_list == ['key1:value1']

        # Modifying tags should invalidate cache
        tag_manager.set_tag('key2', 'value2')
        assert tag_manager._cached_tag_list is None
        third_result = tag_manager.get_tags()
        assert third_result == ['key1:value1', 'key2:value2']

    def test_keyless_and_keyed_same_value(self):
        """Test that a keyless tag and a keyed tag with the same value don't conflict"""
        tag_manager = TagManager()
        # Set a keyless tag
        tag_manager.set_tag(None, 'same_value')
        # Set a keyed tag with the same value
        tag_manager.set_tag('some_key', 'same_value')
        # Set another keyed tag with the same value
        tag_manager.set_tag('another_key', 'same_value')

        # Verify all tags are stored correctly
        assert tag_manager._tags == {
            TagType.KEYLESS: ['same_value'],
            'some_key': ['same_value'],
            'another_key': ['same_value']
        }

        # Verify get_tags includes all tags
        expected = ['another_key:same_value', 'same_value', 'some_key:same_value']
        assert tag_manager.get_tags() == expected

        # Verify we can delete each tag independently
        assert tag_manager.delete_tag(None, 'same_value')
        assert tag_manager._tags == {
            'some_key': ['same_value'],
            'another_key': ['same_value']
        }

        assert tag_manager.delete_tag('some_key', 'same_value')
        assert tag_manager._tags == {
            'another_key': ['same_value']
        }

        assert tag_manager.delete_tag('another_key', 'same_value')
        assert tag_manager._tags == {}
