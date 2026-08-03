# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Allow-list field inclusion for genresources event payloads."""

from __future__ import annotations

import copy
import fnmatch
from collections.abc import Iterator, Mapping, Sequence


class _IncludeAll:
    """Sentinel for ``submit_generic_resource(include=INCLUDE_ALL)``: ship the whole dict as-is."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "INCLUDE_ALL"


#: Pass as ``include`` to ship a caller-constructed dict without an allow-list. Only safe when the
#: integration built every value itself; never use it on a raw upstream object, or it re-opens the leak.
INCLUDE_ALL = _IncludeAll()


def apply_allow_list(
    fields: Mapping[str, object],
    *,
    paths: Sequence[str],
    map_paths: Sequence[str],
    annotation_keys: Sequence[str],
) -> dict:
    """Return a new dict with only the allow-listed parts of ``fields``.

    ``paths`` select plain values (dotted segments; ``[*]`` matches every array element).
    ``map_paths`` select whole flat maps wholesale (e.g. ``metadata.labels``). ``annotation_keys``
    apply fnmatch globs to ``metadata.annotations`` keys; annotations never come in through
    ``paths``/``map_paths``. The input is never mutated.
    """
    src = copy.deepcopy(dict(fields))
    result: dict = {}
    for path in (*paths, *map_paths):
        segments = path.split(".")
        if _targets_annotations(segments):
            continue
        _carve(src, result, segments)

    metadata = result.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("annotations", None)
    _carve_annotations(src, result, annotation_keys)
    _prune_empty(result)
    return result


def find_invalid_include(
    fields: Mapping[str, object],
    paths: Sequence[str],
    map_paths: Sequence[str],
) -> tuple[str, str] | None:
    """Return ``(path, reason)`` for the first invalid include, else None.

    ``paths`` must resolve to values or lists of values; ``map_paths`` must resolve to flat maps.
    """
    for path in paths:
        segments = path.split(".")
        if _targets_annotations(segments):
            continue
        for value in _resolve(fields, segments):
            if not _is_plain_value(value):
                return path, "nested include value"

    for path in map_paths:
        segments = path.split(".")
        if _targets_annotations(segments):
            continue
        for value in _resolve(fields, segments):
            if not _is_flat_map(value):
                return path, "non-flat map_path"

    return None


def _resolve(node: object, segments: list[str]) -> Iterator[object]:
    """Yield each value the path resolves to (one per ``[*]`` element); missing paths yield nothing."""
    if not segments:
        yield node
        return
    head, *rest = segments
    star = head.endswith("[*]")
    key = head[:-3] if star else head
    if not isinstance(node, Mapping) or key not in node:
        return
    value = node[key]
    if star:
        if not isinstance(value, list):
            return
        if not rest:
            yield value
        else:
            for item in value:
                yield from _resolve(item, rest)
    elif rest:
        yield from _resolve(value, rest)
    else:
        yield value


def _is_plain_value(value: object) -> bool:
    """True for a value (str/int/float/bool), ``None``, or a list of those; a map is never a plain value."""
    if isinstance(value, Mapping):
        return False
    if isinstance(value, list):
        return all(not isinstance(item, (Mapping, list)) for item in value)
    return True


def _is_flat_map(value: object) -> bool:
    """True for a map whose values are all plain (no nested objects or lists)."""
    return isinstance(value, Mapping) and all(not isinstance(v, (Mapping, list)) for v in value.values())


def _targets_annotations(segments: list[str]) -> bool:
    """True if the path touches an ``annotations`` map at any depth."""
    return any(segment.removesuffix("[*]") == "annotations" for segment in segments)


def _carve(src_node: object, dst_node: dict, segments: list[str]) -> bool:
    """Copy the value at ``segments`` into ``dst_node``; return True iff a value was copied.

    A container is attached only once a descendant copies data, so a missing path leaves no shell.
    Existing containers are reused, so paths sharing a prefix merge (per element for ``[*]``).
    """
    head, *rest = segments
    star = head.endswith("[*]")
    key = head[:-3] if star else head

    if not isinstance(src_node, Mapping) or key not in src_node:
        return False
    src_value = src_node[key]

    if not star:
        if not rest:
            dst_node[key] = copy.deepcopy(src_value)
            return True
        if not isinstance(src_value, Mapping):
            return False
        child = dst_node.get(key)
        created = not isinstance(child, dict)
        if created:
            child = {}
        copied = _carve(src_value, child, rest)
        if copied and created:
            dst_node[key] = child
        return copied

    if not isinstance(src_value, list):
        return False
    dst_list = dst_node.get(key)
    created = not isinstance(dst_list, list)
    if created:
        dst_list = []
    any_copied = False
    for index, item in enumerate(src_value):
        while len(dst_list) <= index:
            dst_list.append({})
        if not rest:
            dst_list[index] = copy.deepcopy(item)
            any_copied = True
        elif isinstance(item, Mapping) and isinstance(dst_list[index], dict):
            if _carve(item, dst_list[index], rest):
                any_copied = True
    if any_copied and created:
        dst_node[key] = dst_list
    return any_copied


def _carve_annotations(src: Mapping[str, object], dst: dict, annotation_keys: Sequence[str]) -> None:
    """Add the allow-listed ``metadata.annotations`` (plain values only) to ``dst``."""
    metadata = src.get("metadata")
    annotations = metadata.get("annotations") if isinstance(metadata, Mapping) else None
    if not isinstance(annotations, Mapping):
        return
    kept = {}
    for pattern in annotation_keys:
        for key, value in annotations.items():
            if fnmatch.fnmatchcase(key, pattern) and not isinstance(value, (Mapping, list)):
                kept[key] = copy.deepcopy(value)
    if kept:
        dst.setdefault("metadata", {})
        if isinstance(dst["metadata"], dict):
            dst["metadata"]["annotations"] = kept


def _prune_empty(node: object) -> None:
    """Remove empty dicts and empty lists in-place, bottom-up; values and ``None`` are kept."""
    if isinstance(node, dict):
        for key in list(node):
            value = node[key]
            _prune_empty(value)
            if value == {} or value == []:
                del node[key]
    elif isinstance(node, list):
        for item in node:
            _prune_empty(item)
        node[:] = [item for item in node if item != {} and item != []]
