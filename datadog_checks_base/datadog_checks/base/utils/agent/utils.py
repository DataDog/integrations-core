# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

LOGGER = logging.getLogger(__file__)


def should_profile_memory(datadog_agent, check_name):
    tracemalloc_include = (
        datadog_agent.get_config('tracemalloc_include') or datadog_agent.get_config('tracemalloc_whitelist') or ''
    )
    tracemalloc_include = [check.strip() for check in tracemalloc_include.split(',') if check]

    tracemalloc_exclude = (
        datadog_agent.get_config('tracemalloc_exclude') or datadog_agent.get_config('tracemalloc_blacklist') or ''
    )
    tracemalloc_exclude = [check.strip() for check in tracemalloc_exclude.split(',') if check]

    if datadog_agent.get_config('tracemalloc_include') and datadog_agent.get_config('tracemalloc_whitelist'):
        LOGGER.warning(
            'Found both tracemalloc_include and tracemalloc_whitelist, only tracemalloc_include will be used'
        )

    if datadog_agent.get_config('tracemalloc_exclude') and datadog_agent.get_config('tracemalloc_blacklist'):
        LOGGER.warning(
            'Found both tracemalloc_exclude and tracemalloc_blacklist, only tracemalloc_exclude will be used'
        )

    return check_name not in tracemalloc_exclude and (
        check_name in tracemalloc_include if tracemalloc_include else True
    )
