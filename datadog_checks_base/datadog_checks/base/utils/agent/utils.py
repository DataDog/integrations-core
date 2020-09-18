# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def should_profile_memory(datadog_agent, check_name):
    tracemalloc_include = datadog_agent.get_config('tracemalloc_include') or datadog_agent.get_config('tracemalloc_whitelist') or ''
    if tracemalloc_include:
        tracemalloc_include = [check.strip() for check in tracemalloc_include.split(',')]
        tracemalloc_include = [check for check in tracemalloc_include if check]

    tracemalloc_exclude = datadog_agent.get_config('tracemalloc_exclude') or datadog_agent.get_config('tracemalloc_blacklist') or ''
    if tracemalloc_exclude:
        tracemalloc_exclude = [check.strip() for check in tracemalloc_exclude.split(',')]
        tracemalloc_exclude = [check for check in tracemalloc_exclude if check]

    return check_name not in tracemalloc_exclude and (
        check_name in tracemalloc_include if tracemalloc_include else True
    )
