import pytest

from datadog_checks.mysql.tag_manager import TagManager, TagType


class TestTagManager:
    def test_init(self):
        """Test initialization of TagManager"""
        tag_manager = TagManager()
        assert tag_manager._tags == {}
        assert tag_manager._cached_tag_list is None
        assert tag_manager._keyless == TagType.KEYLESS

    @pytest.mark.parametrize(
        'key,value,internal,expected_tags,expected_internal_tags',
        [
            ('test_key', 'test_value', False, {'test_key': ['test_value']}, {}),
            ('test_key', 'test_value', True, {}, {'test_key': ['test_value']}),
            (None, 'test_value', False, {TagType.KEYLESS: ['test_value']}, {}),
            (None, 'test_value', True, {}, {TagType.KEYLESS: ['test_value']}),
        ],
    )
    def test_set_tag(self, key, value, internal, expected_tags, expected_internal_tags):
        """Test setting tags with various combinations of key, value, and internal status"""
        tag_manager = TagManager()
        tag_manager.set_tag(key, value, internal=internal)
        assert tag_manager._tags == expected_tags
        assert tag_manager._internal_tags == expected_internal_tags
        assert tag_manager._cached_tag_list is None
        assert tag_manager._cached_internal_tag_list is None

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

    @pytest.mark.parametrize(
        'key,values,delete_key,delete_value,internal,expected_tags,expected_internal_tags,description',
        [
            (
                'test_key',
                ['value1', 'value2'],
                'test_key',
                'value1',
                False,
                {'test_key': ['value2']},
                {},
                'deleting specific value',
            ),
            ('test_key', ['value1', 'value2'], 'test_key', None, False, {}, {}, 'deleting all values for key'),
            (
                None,
                ['value1', 'value2'],
                None,
                'value1',
                False,
                {TagType.KEYLESS: ['value2']},
                {},
                'deleting specific keyless value',
            ),
            (None, ['value1', 'value2'], None, None, False, {}, {}, 'deleting all keyless values'),
            (
                'test_key',
                ['value1', 'value2'],
                'test_key',
                'value1',
                True,
                {},
                {'test_key': ['value2']},
                'deleting specific internal value',
            ),
        ],
    )
    def test_delete_tag(
        self, key, values, delete_key, delete_value, internal, expected_tags, expected_internal_tags, description
    ):
        """Test various tag deletion scenarios"""
        tag_manager = TagManager()
        # Set up initial tags
        for value in values:
            tag_manager.set_tag(key, value, internal=internal)

        # Generate initial cache
        tag_manager.get_tags(include_internal=True)
        assert tag_manager._cached_tag_list is not None
        assert tag_manager._cached_internal_tag_list is not None

        # Perform deletion
        assert tag_manager.delete_tag(delete_key, delete_value, internal=internal)

        # Verify cache is invalidated
        if internal:
            assert tag_manager._cached_internal_tag_list is None
        else:
            assert tag_manager._cached_tag_list is None

        # Verify internal state
        assert tag_manager._tags == expected_tags
        assert tag_manager._internal_tags == expected_internal_tags

    @pytest.mark.parametrize(
        'initial_tags,tag_list,replace,expected_tags,description',
        [
            (
                [],
                ['key1:value1', 'key2:value2', 'value3'],
                False,
                ['key1:value1', 'key2:value2', 'value3'],
                'setting new tags',
            ),
            (['key1:old_value'], ['key1:new_value'], True, ['key1:new_value'], 'replacing existing tags'),
            (
                ['key1:old_value'],
                ['key1:new_value'],
                False,
                ['key1:new_value', 'key1:old_value'],
                'appending to existing tags',
            ),
            ([], ['key1:value1', 'key1:value1'], False, ['key1:value1'], 'setting duplicate values'),
            (
                [],
                ['key1:value1', 'value2', 'key2:value3'],
                False,
                ['key1:value1', 'key2:value3', 'value2'],
                'setting mixed format tags',
            ),
        ],
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

    @pytest.mark.parametrize(
        'regular_tags,internal_tags,include_internal,expected_tags',
        [
            ({'key1': ['value1']}, {'key2': ['value2']}, True, ['key1:value1', 'key2:value2']),
            ({'key1': ['value1']}, {'key2': ['value2']}, False, ['key1:value1']),
            ({'key1': ['value1']}, {'key1': ['value2']}, True, ['key1:value1', 'key1:value2']),
            ({'key1': ['value1']}, {'key1': ['value2']}, False, ['key1:value1']),
        ],
    )
    def test_get_tags(self, regular_tags, internal_tags, include_internal, expected_tags):
        """Test getting tags with various combinations of regular and internal tags"""
        tag_manager = TagManager()

        # Set up regular tags
        for key, values in regular_tags.items():
            for value in values:
                tag_manager.set_tag(key, value)

        # Set up internal tags
        for key, values in internal_tags.items():
            for value in values:
                tag_manager.set_tag(key, value, internal=True)

        # Verify tags
        assert sorted(tag_manager.get_tags(include_internal=include_internal)) == sorted(expected_tags)

    def test_cache_management(self):
        """Test that tag caches are properly managed"""
        tag_manager = TagManager()

        # Set initial tags
        tag_manager.set_tag('regular_key', 'regular_value')
        tag_manager.set_tag('internal_key', 'internal_value', internal=True)

        # First call should generate both caches
        _ = tag_manager.get_tags(include_internal=True)
        assert tag_manager._cached_tag_list is not None
        assert tag_manager._cached_internal_tag_list is not None

        # Modify regular tags
        tag_manager.set_tag('regular_key2', 'regular_value2')
        assert tag_manager._cached_tag_list is None
        assert tag_manager._cached_internal_tag_list is not None

        # Modify internal tags
        tag_manager.set_tag('internal_key2', 'internal_value2', internal=True)
        assert tag_manager._cached_internal_tag_list is None

        # Verify all tags are included
        second_result = tag_manager.get_tags(include_internal=True)
        assert 'regular_key:regular_value' in second_result
        assert 'regular_key2:regular_value2' in second_result
        assert 'internal_key:internal_value' in second_result
        assert 'internal_key2:internal_value2' in second_result
