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
        # Cache for the list of tag strings
        self._cached_tag_list: Optional[List[str]] = None
        # Special key for keyless tags
        self._keyless: TagType = TagType.KEYLESS

    def set_tag(self, key: Optional[str], value: str, replace: bool = False) -> None:
        """
        Set a tag with the given key and value.
        If key is None or empty, the value is stored as a keyless tag.

        Args:
            key (str): The tag key, or None/empty for keyless tags
            value (str): The tag value
            replace (bool): If True, replaces all existing values for this key
                           If False, appends the value if it doesn't exist
        """
        if not key:
            key = self._keyless

        if replace or key not in self._tags:
            self._tags[key] = [value]
        elif value not in self._tags[key]:
            self._tags[key].append(value)

        # Invalidate the cache since tags have changed
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

    def delete_tag(self, key: Optional[str], value: Optional[str] = None) -> bool:
        """
        Delete a tag or specific value for a tag.
        For keyless tags, use None or empty string as the key.

        Args:
            key (str): The tag key to delete, or None/empty for keyless tags
            value (str, optional): If provided, only deletes this specific value for the key.
                                 If None, deletes all values for the key.

        Returns:
            bool: True if something was deleted, False otherwise
        """
        if not key:
            key = self._keyless

        if key not in self._tags:
            return False

        if value is None:
            # Delete the entire key
            del self._tags[key]
            self._cached_tag_list = None
            return True
        else:
            # Delete specific value if it exists
            if value in self._tags[key]:
                self._tags[key].remove(value)
                # Clean up empty lists
                if not self._tags[key]:
                    del self._tags[key]
                self._cached_tag_list = None
                return True
        return False

    def get_tags(self) -> List[str]:
        """
        Get a list of tag strings.
        For key-value tags, returns "key:value" format.
        For keyless tags, returns just the value.
        The returned list is always sorted alphabetically.

        Returns:
            list: Sorted list of tag strings
        """
        # Return cached list if available
        if self._cached_tag_list is not None:
            return self._cached_tag_list

        # Generate new list of tag strings
        tag_strings: List[str] = []
        for key, values in self._tags.items():
            for value in values:
                if key == self._keyless:
                    tag_strings.append(value)
                else:
                    tag_strings.append(f"{key}:{value}")

        # Sort and cache the result
        self._cached_tag_list = sorted(tag_strings)
        return self._cached_tag_list
