import re


# The DiscoveryFilter class allows to filter a list of values or identifiers passed to the 'match' method
# by obtaining the subset of values from that list that match the specified configuration.
# The config has two main parts:
# 'keys' (string value configurable by parameter): List of values that will be searched for in the list of items
# to be filtered and will be included in the list of matches returned if they match (simple string comparison).
# They may be of type string or key/value.
# If its key is found in the list, the tuple formed by the key/value or
# key/None in the case of being a string type will be returned.
# 'discovery': It is the part of the configuration that will allow the 'autodiscover' feature within a list of values.
# It works by comparing patterns following the following criteria:
# The elements of the list to be filtered that match any regular expression included in the 'include' key of 'discovery'
# (or default_include list) and do not match any of the regular expressions of the 'exclude' key of 'discovery'
# (or default_exclude list).
# The include patterns will be processed in order
# The maximum number of elements to be returned by the 'autodiscovery' part will be the one indicated in the 'limit' key
# (or default_limit)
# Different examples of these configurations can be seen in test_unit_projects.py inside tests
class DiscoveryFilter:
    def __init__(
        self,
        name,
        log,
        config,
        items_id='keys',
        default_limit=10,
        default_include=None,
        default_exclude=None,
    ):
        self._log = log
        self._items_id = items_id
        self._config = config
        self._default_limit = default_limit
        self._default_include = [] if default_include is None else default_include
        self._default_exclude = [] if default_exclude is None else default_exclude
        self._log.debug('`%s` config: %s', name, self._config)

    def match(self, items):
        self._log.debug('trying to match: %s', items)
        self._log.debug('self._config: %s', self._config)
        matched_items = self._match_items(items)
        matched_items.extend(self._match_discovery(matched_items, items))
        return matched_items

    def _match_items(self, items):
        matched_id = []
        self._log.debug('matching items')
        self._log.debug('items: %s', items)
        if self._config is not None and isinstance(self._config, dict):
            config_items_id = self._config.get(self._items_id, None)
            self._log.debug('config_items_id: %s', config_items_id)
            if config_items_id:
                for id_item in config_items_id:
                    id_key, id_value = None, None
                    if isinstance(id_item, dict):
                        id_key = next(iter(id_item))
                        id_value = next(iter(id_item.values()))
                    elif isinstance(id_item, str):
                        id_key = id_item
                    if id_key not in [key for key, _ in matched_id]:
                        if id_key in items:
                            self._log.debug('`%s` item matched', id_key)
                            matched_id.append(tuple([id_key, id_value]))
                        else:
                            self._log.warning('`%s` item not found in items', id_key)
                    else:
                        self._log.debug('`%s` item was already matched', id_key)
        return matched_id

    def _match_discovery(self, matched_items, items):
        matched_discovery = []
        self._log.debug('matching discovery')
        self._log.debug('matched_items: %s', matched_items)
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
                pattern = (
                    include_pattern
                    if isinstance(include_pattern, str)
                    else next(iter(include_pattern.keys()))
                    if isinstance(include_pattern, dict) and len(include_pattern) == 1
                    else None
                )
                if pattern:
                    pattern_config = (
                        next(iter(include_pattern.values()))
                        if isinstance(include_pattern, dict) and len(include_pattern) == 1
                        else None
                    )
                    for item in items:
                        if len(matched_discovery) == limit:
                            return matched_discovery
                        if (
                            item not in [key for key, _ in matched_items]
                            and item not in [key for key, _ in matched_discovery]
                            and item not in excluded_items
                            and re.search(
                                pattern,
                                item,
                            )
                        ):
                            matched_discovery.append(
                                (
                                    item,
                                    pattern_config,
                                )
                            )
        return matched_discovery
