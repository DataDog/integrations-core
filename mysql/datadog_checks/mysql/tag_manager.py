from enum import Enum, auto
from typing import Dict, List, Optional, Union, Any

class TagType(Enum):
    """Enum for different types of tags"""
    KEYLESS = auto()

class TagManager:
    def __init__(self) -> None:
        # Internal data structure to store tags
        # Format: {key: [value1, value2, ...]}
        self._tags: Dict[Union[str, TagType], List[str]] = {}
        # Internal data structure for internal tags
        self._internal_tags: Dict[Union[str, TagType], List[str]] = {}
        # Cache for the list of tag strings
        self._cached_tag_list: Optional[List[str]] = None
        # Cache for the list of internal tag strings
        self._cached_internal_tag_list: Optional[List[str]] = None
        # Special key for keyless tags
        self._keyless: TagType = TagType.KEYLESS

    def set_tag(self, key: Optional[str], value: str, replace: bool = False, internal: bool = False) -> None:
        """
        Set a tag with the given key and value.
        If key is None or empty, the value is stored as a keyless tag.

        Args:
            key (str): The tag key, or None/empty for keyless tags
            value (str): The tag value
            replace (bool): If True, replaces all existing values for this key
                           If False, appends the value if it doesn't exist
            internal (bool): If True, stores the tag in internal storage
        """
        if not key:
            key = self._keyless

        target_tags = self._internal_tags if internal else self._tags
        target_cache = self._cached_internal_tag_list if internal else self._cached_tag_list

        if replace or key not in target_tags:
            target_tags[key] = [value]
        elif value not in target_tags[key]:
            target_tags[key].append(value)

        # Invalidate the appropriate cache since tags have changed
        if internal:
            self._cached_internal_tag_list = None
        else:
            self._cached_tag_list = None

    def set_tags_from_list(self, tag_list: List[str], replace: bool = False) -> None:
        """
        Set multiple tags from a list of strings.
        Strings can be in "key:value" format or just "value" format.

        Args:
            tag_list (List[str]): List of tags in "key:value" format or just "value"
            replace (bool): If True, replace existing values for keys
        """
        for tag in tag_list:
            if ':' in tag:
                key, value = tag.split(':', 1)
                self.set_tag(key, value, replace=replace)
            else:
                self.set_tag(None, tag, replace=replace)

    def delete_tag(self, key: Optional[str], value: Optional[str] = None, internal: bool = False) -> bool:
        """
        Delete a tag or specific value for a tag.
        For keyless tags, use None or empty string as the key.

        Args:
            key (str): The tag key to delete, or None/empty for keyless tags
            value (str, optional): If provided, only deletes this specific value for the key.
                                 If None, deletes all values for the key.
            internal (bool): If True, deletes from internal storage

        Returns:
            bool: True if something was deleted, False otherwise
        """
        if not key:
            key = self._keyless

        target_tags = self._internal_tags if internal else self._tags

        if key not in target_tags:
            return False

        if value is None:
            # Delete the entire key
            del target_tags[key]
            # Invalidate the appropriate cache
            if internal:
                self._cached_internal_tag_list = None
            else:
                self._cached_tag_list = None
            return True
        else:
            # Delete specific value if it exists
            if value in target_tags[key]:
                target_tags[key].remove(value)
                # Clean up empty lists
                if not target_tags[key]:
                    del target_tags[key]
                # Invalidate the appropriate cache
                if internal:
                    self._cached_internal_tag_list = None
                else:
                    self._cached_tag_list = None
                return True
        return False

    def _generate_tag_strings(self, tags_dict: Dict[Union[str, TagType], List[str]]) -> List[str]:
        """
        Generate a list of tag strings from a tags dictionary.

        Args:
            tags_dict (Dict[Union[str, TagType], List[str]]): Dictionary of tags to convert to strings

        Returns:
            List[str]: List of tag strings
        """
        tag_strings: List[str] = []
        for key, values in tags_dict.items():
            for value in values:
                if key == self._keyless:
                    tag_strings.append(value)
                else:
                    tag_strings.append(f"{key}:{value}")
        return tag_strings

    def get_tags(self, include_internal: bool = True) -> List[str]:
        """
        Get a list of tag strings.
        For key-value tags, returns "key:value" format.
        For keyless tags, returns just the value.
        The returned list is always sorted alphabetically.

        Args:
            include_internal (bool): If True, includes internal tags in the result

        Returns:
            list: Sorted list of tag strings
        """
        if not include_internal:
            # Return cached list if available
            if self._cached_tag_list is not None:
                return self._cached_tag_list

            # Generate and cache regular tags
            self._cached_tag_list = sorted(self._generate_tag_strings(self._tags))
            return self._cached_tag_list

        # For combined tags, try to use cached lists first
        if self._cached_tag_list is None:
            self._cached_tag_list = sorted(self._generate_tag_strings(self._tags))

        if self._cached_internal_tag_list is None:
            self._cached_internal_tag_list = sorted(self._generate_tag_strings(self._internal_tags))

        # Combine the cached lists
        return sorted(self._cached_tag_list + self._cached_internal_tag_list)
