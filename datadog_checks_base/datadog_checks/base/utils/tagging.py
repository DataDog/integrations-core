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
    A data structure to manage a collection of tags (key:value pairs).

    Supports:
      - add_tag(key, value): add one or more tags under the same key
      - add_unique_tag(key, value): add a tag ensuring the key is unique (replaces any existing tags with that key)
      - get_tag(key): return a set of all values for the given key
      - get_tags(sort=True): return a sorted list of (key, value) tuples
      - iteration: iterate over tags yielding (key, value) tuples
      - remove_tag(key, value=None): remove all tags under a given key, or a specific key:value tag if value is provided
      - clear(): remove all tags
    """

    def __init__(self) -> None:
        self._data: dict[str, set[str]] = {}

    def add_tag(self, key: str, value: str) -> None:
        """Add a tag under given key."""
        if key not in self._data:
            self._data[key] = set()
        self._data[key].add(value)

    def add_unique_tag(self, key: str, value: str) -> None:
        """Add a tag under given key, ensuring the key has only this value."""
        self._data[key] = {value}

    def get_tag(self, key: str) -> set[str]:
        """Return all values for the given key. Returns an empty set if key doesn't exist."""
        return self._data.get(key, set())

    def get_tags(self, sort: bool = True) -> list[tuple[str, str]]:
        """Return all tags as a list of (key, value) tuples, sorted if requested."""
        tags_list: list[tuple[str, str]] = []
        for key, values in self._data.items():
            for val in values:
                tags_list.append((key, val))
        return sorted(tags_list) if sort else tags_list

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

    def __iter__(self) -> Iterator[tuple[str, str]]:
        """Allow iteration over tags: for tag in ts or list(ts)."""
        return iter(self.get_tags())

    def clear(self) -> None:
        """Remove all tags."""
        self._data.clear()
