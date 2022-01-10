# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

try:
    import orjson as json

    impl = 'orjson'
    sort_keys_kwargs = {'option': json.OPT_SORT_KEYS}
except ImportError:
    import json

    impl = 'stdlib'
    sort_keys_kwargs = {'sort_keys': True}

logger = logging.getLogger(__name__)
logger.debug('Using JSON implementation from %s', impl)

__all__ = ['json']
