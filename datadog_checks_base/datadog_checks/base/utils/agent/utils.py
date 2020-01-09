# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def should_profile_memory(datadog_agent, check_name):
    tracemalloc_whitelist = datadog_agent.get_config('tracemalloc_whitelist') or ''
    if tracemalloc_whitelist:
        tracemalloc_whitelist = [check.strip() for check in tracemalloc_whitelist.split(',')]
        tracemalloc_whitelist = [check for check in tracemalloc_whitelist if check]

    tracemalloc_blacklist = datadog_agent.get_config('tracemalloc_blacklist') or ''
    if tracemalloc_blacklist:
        tracemalloc_blacklist = [check.strip() for check in tracemalloc_blacklist.split(',')]
        tracemalloc_blacklist = [check for check in tracemalloc_blacklist if check]

    return check_name not in tracemalloc_blacklist and (
        check_name in tracemalloc_whitelist if tracemalloc_whitelist else True
    )
