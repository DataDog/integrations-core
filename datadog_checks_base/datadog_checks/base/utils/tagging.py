# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from collections.abc import Iterator

try:
    import tagger
except ImportError:
    from datadog_checks.base.stubs import tagger  # noqa: F401


GENERIC_TAGS: set[str] = {
    'cluster_name',
    'clustername',
    'cluster',
    'clusterid',
    'cluster_id',
    'env',
    'host_name',
    'hostname',
    'host',
    'service',
    'version',
}


class TagsSet:
    """
    A data structure to manage a collection of tags supporting both formats:
      - key:value pairs
      - standalone values (stored with empty string key)

    Supports:
      - add(tag_string): add a tag in 'key:value' or 'value' format
      - add_tag(key, value): add a key-value pair tag
      - add_standalone_tag(value): add a standalone value tag
      - add_unique_tag(key, value): add a tag ensuring the key has only this value
      - get_tag(key): return a set of all values for the given key
      - get_tags(sort=True): return a list of formatted tag strings
      - iteration: iterate over tags yielding (key, value) tuples
      - remove(tag_string): remove a tag in 'key:value' or 'value' format
      - remove_tag(key, value=None): remove all tags under a given key, or a specific key:value tag
      - clear(): remove all tags
    """

    def __init__(self) -> None:
        self._data: dict[str, set[str]] = {}

    def add_tag(self, key: str, value: str) -> None:
        """Add a tag with explicit key and value.

        For standalone value tags, use add_standalone_tag() instead.

        Raises:
            ValueError: If key is empty
        """
        if not key:
            raise ValueError("Tag key cannot be empty. Use add_standalone_tag() for standalone values.")

        if key not in self._data:
            self._data[key] = set()
        self._data[key].add(value)

    def add_standalone_tag(self, value: str) -> None:
        """Add a standalone value tag (no key).

        Standalone tags are stored internally with an empty key.
        """
        if '' not in self._data:
            self._data[''] = set()
        self._data[''].add(value)

    def add_unique_tag(self, key: str, value: str) -> None:
        """Add a tag under given key, ensuring the key has only this value.

        Raises:
            ValueError: If key is empty
        """
        if not key:
            raise ValueError("Tag key cannot be empty. Use add_standalone_tag() for standalone values.")
        self._data[key] = {value}

    def get_tag(self, key: str) -> set[str]:
        """Return all values for the given key. Returns an empty set if key doesn't exist."""
        return self._data.get(key, set())

    def get_standalone_tags(self) -> set[str]:
        return self.get_tag('')

    def _get_tag_tuples(self, sort: bool = True) -> list[tuple[str, str]]:
        """Return all tags as a list of (key, value) tuples, sorted if requested."""
        tags_list: list[tuple[str, str]] = []
        for key, values in self._data.items():
            for val in values:
                tags_list.append((key, val))
        return sorted(tags_list) if sort else tags_list

    def get_tags(self, sort: bool = True) -> list[str]:
        """Return all tags as a list of formatted strings, sorted if requested.

        Returns tags in their original format:
        - 'key:value' for key-value pairs
        - 'value' for standalone values
        """
        tags = []
        for key, value in self._get_tag_tuples(sort=False):
            if key:
                tags.append(f"{key}:{value}")
            else:
                tags.append(value)
        return sorted(tags) if sort else tags

    def remove_tag(self, key: str, value: str | None = None) -> None:
        """Remove tag(s) under the given key.

        If value is None, remove all tags under the given key.
        If value is provided, remove only the specific key:value tag.
        """
        if value is None:
            self._data.pop(key, None)
        else:
            if key in self._data:
                self._data[key].discard(value)
                if not self._data[key]:
                    del self._data[key]

    def clear(self) -> None:
        """Remove all tags."""
        self._data.clear()

    def __iter__(self) -> Iterator[tuple[str, str]]:
        """Allow iteration over tags: for tag in ts or list(ts)."""
        return iter(self._get_tag_tuples())
