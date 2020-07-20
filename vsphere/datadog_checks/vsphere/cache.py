# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, Iterator, List, Type

from pyVmomi import vim
from six import iterkeys

from datadog_checks.vsphere.types import CounterId, MetricName, ResourceTags


class VSphereCache(object):
    """
    Wraps configuration and status for the Morlist and Metadata caches.
    VSphereCache is *not* threadsafe.
    """

    def __init__(self, interval_sec):
        # type: (int) -> None
        self._last_ts = 0  # type: float
        self._interval = interval_sec
        self._content = {}  # type: Dict[Any, Any]

    @contextmanager
    def update(self):
        # type: () -> Generator[None, None, None]
        """A context manager to allow modification of the cache. It will restore the previous value
        on any error.
        Usage:
        ```
            with cache.update():
                cache.set_XXX(SOME_DATA)
        ```
        """
        old_content = self._content
        self._content = {}  # 1. clear the content
        try:
            yield  # 2. Actually update the cache
            self._last_ts = time.time()  # 3. Cache was updated successfully
        except Exception:
            # Restore old data
            self._content = old_content
            raise

    def is_expired(self):
        # type: () -> bool
        """The cache has a global time to live, all elements expire at the same time.
        :return True if the cache is expired."""
        elapsed = time.time() - self._last_ts
        return elapsed > self._interval


class MetricsMetadataCache(VSphereCache):
    """A VSphere cache dedicated to store the metrics metadata from a user environment.
    Data is stored like this:

    _content = {
        vim.HostSystem: {
            <COUNTER_ID>: <DD_METRIC_NAME>,
            ...
        },
        vim.VirtualMachine: {...},
        ...
    }
    """

    def get_metadata(self, resource_type):
        # type: (Type[vim.ManagedEntity]) -> Dict[CounterId, MetricName]
        return self._content[resource_type]

    def set_metadata(self, resource_type, metadata):
        # type: (Type[vim.ManagedEntity], Dict[CounterId, MetricName]) -> None
        self._content[resource_type] = metadata


class InfrastructureCache(VSphereCache):
    """A VSphere cache dedicated to store the infrastructure data from a user environment.
    Tags and properties coming from the SOAP API are stored separately for easier manipulation.
    'tags' is only populated if configured correctly in the conf.yaml file.
    Data is stored like this:

    _content = {
        'mors': {
            vim.VirtualMachine: {
                <MOR_REFERENCE>: <MOR_PROPS_DICT>
            },
            ...
        },
        'tags': {
            <RESOURCE_TYPE>: {
                <RESOURCE_MOR_ID>: ['<CATEGORY_NAME>:<TAG_NAME>', ...]
            },
        }
        ...
    }
    """

    @property
    def _mors(self):
        # type: () -> Dict[Type[vim.ManagedEntity], Dict[vim.ManagedEntity, Any]]
        if 'mors' not in self._content:
            self._content['mors'] = {}
        return self._content['mors']

    @_mors.setter
    def _mors(self, value):
        # type: (Dict[vim.ManagedEntity, Dict[str, Any]]) -> None
        self._content['mors'] = value

    @property
    def _tags(self):
        # type: () -> ResourceTags
        if 'tags' not in self._content:
            self._content['tags'] = {}
        return self._content['tags']

    @_tags.setter
    def _tags(self, value):
        # type: (ResourceTags) -> None
        self._content['tags'] = value

    def get_mor_tags(self, mor):
        # type: (vim.ManagedEntity) -> List[str]
        """
        :return: list of mor tags or empty list if mor is not found.
        """
        mor_type = type(mor)
        return self._tags.get(mor_type, {}).get(mor._moId, [])

    def set_all_tags(self, mor_tags):
        # type: (ResourceTags) -> None
        self._tags = mor_tags

    def get_mor_props(self, mor, default=None):
        # type: (vim.ManagedEntity, Dict[str, Any]) -> Dict[str, Any]
        mor_type = type(mor)
        return self._mors.get(mor_type, {}).get(mor, default)

    def get_mors(self, resource_type):
        # type: (Type[vim.ManagedEntity]) -> Iterator[vim.ManagedEntity]
        return iterkeys(self._mors.get(resource_type, {}))

    def set_mor_props(self, mor, mor_data):
        # type: (vim.ManagedEntity, Dict[str, Any]) -> None
        mor_type = type(mor)
        if mor_type not in self._mors:
            self._mors[mor_type] = {}
        self._mors[mor_type][mor] = mor_data
