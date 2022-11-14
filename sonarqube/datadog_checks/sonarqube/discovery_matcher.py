import re
from typing import List

from datadog_checks.base import ConfigurationError


class DiscoveryMatcher:
    def __init__(
        self,
        name: str,
        log,
        config: dict,
        mandatory: bool = True,
        items_id: str = 'keys',
        default_limit: int = 10,
        default_include: list = None,
        default_exclude: list = None,
    ):
        self._log = log
        self._items_id = items_id
        self._config = config
        self._default_limit = default_limit
        self._default_include = [] if default_include is None else default_include
        self._default_exclude = [] if default_exclude is None else default_exclude
        self._log.debug('\'%s\' config: %s', name, self._config)
        if self._config is None and mandatory:
            raise ConfigurationError('\'{}\' setting must be defined'.format(name))

    def match(self, items: List[str]) -> List[tuple]:
        self._log.debug('trying to match: %s', items)
        matched_items = self._match_items(items)
        matched_items.extend(self._match_discovery(matched_items, items))
        return matched_items

    def _match_items(self, items: List[str]) -> List[tuple]:
        matched_id = []
        self._log.debug('matching items')
        self._log.debug('self._config: %s', self._config)
        if self._config is not None and isinstance(self._config, dict):
            config_items_id = self._config.get(self._items_id, None)
            self._log.debug('config_items_id: %s', config_items_id)
            if config_items_id:
                for id_item in config_items_id:
                    id_key = (
                        id_item
                        if isinstance(id_item, str)
                        else list(id_item.keys())[0]
                        if isinstance(id_item, dict) and len(id_item) == 1
                        else None
                    )
                    id_value = list(id_item.values())[0] if isinstance(id_item, dict) and len(id_item) == 1 else None
                    if id_key not in [key for key, value in matched_id]:
                        if id_key in items:
                            self._log.debug('\'%s\' item matched', id_key)
                            matched_id.append(tuple([id_key, id_value]))
                        else:
                            self._log.warning('\'%s\' item not found in items', id_key)
                    else:
                        self._log.debug('\'%s\' item was already matched', id_key)
        return matched_id

    def _match_discovery(self, matched_items: List[tuple], items: List[str]):
        matched_discovery = []
        self._log.debug('matching discovery')
        self._log.debug('self._config: %s', self._config)
        self._log.debug('items: %s', items)
        if self._config is not None and isinstance(self._config, dict):
            config_key_discovery = self._config.get('discovery', None)
            self._log.debug('config_key_discovery: %s', config_key_discovery)
            if config_key_discovery is None:
                limit = self._default_limit
                exclude_patterns = self._default_exclude
                include_patterns = self._default_include
            else:
                limit = config_key_discovery.get('limit', self._default_limit)
                exclude_patterns = config_key_discovery.get('exclude', self._default_exclude)
                include_patterns = config_key_discovery.get('include', self._default_include)
            excluded_items = []
            for item in items:
                for exclude_pattern in exclude_patterns:
                    if re.search(exclude_pattern, item):
                        excluded_items.append(item)
                        break
            self._log.debug('limit: %d', limit)
            self._log.debug('exclude_patterns: %s', exclude_patterns)
            self._log.debug('include_patterns: %s', include_patterns)
            self._log.debug('excluded_items: %s', excluded_items)
            for include_pattern in include_patterns:
                for item in items:
                    if len(matched_discovery) == limit:
                        return matched_discovery
                    if (
                        item not in [key for key, _ in matched_items]
                        and item not in [key for key, _ in matched_discovery]
                        and item not in excluded_items
                        and re.search(
                            include_pattern
                            if isinstance(include_pattern, str)
                            else list(include_pattern.keys())[0]
                            if isinstance(include_pattern, dict) and len(include_pattern) == 1
                            else None,
                            item,
                        )
                    ):
                        matched_discovery.append(
                            (
                                item,
                                list(include_pattern.values())[0]
                                if isinstance(include_pattern, dict) and len(include_pattern) == 1
                                else None,
                            )
                        )
        return matched_discovery
