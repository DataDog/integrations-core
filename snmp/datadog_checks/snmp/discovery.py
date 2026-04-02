# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import asyncio
import json
import time
import weakref  # noqa: F401
from typing import TYPE_CHECKING

from datadog_checks.base import ConfigurationError

from .compat import write_persistent_cache
from .config import InstanceConfig  # noqa: F401

if TYPE_CHECKING:
    from .snmp import SnmpCheck  # noqa: F401


def discover_instances(config, interval, check_ref):
    # type: (InstanceConfig, float, weakref.ref[SnmpCheck]) -> None
    """Function looping over a subnet to discover devices, meant to run in a thread.

    This is extracted from the check class to not keep a strong reference to
    the check instance. This way if the agent unschedules the check and deletes
    the reference to the instance, the check is garbage collected properly and
    that function can stop.
    """
    # pysnmp 7.x uses asyncio; worker threads have no event loop by default in Python 3.10+.
    # Save and restore the current loop so that callers (e.g. tests) that already have a
    # loop in this thread don't lose it when we clean up.
    try:
        _prev_loop = asyncio.get_event_loop()
    except RuntimeError:
        _prev_loop = None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        while True:
            start_time = time.time()
            for host in config.network_hosts():
                check = check_ref()
                if check is None or not check._running:
                    return

                host_config = check._build_autodiscovery_config(config.instance, host)

                try:
                    sys_object_oid = check.fetch_sysobject_oid(host_config)
                except Exception as e:
                    check.log.debug("Error scanning host %s: %s", host, e)
                    del check
                    continue
                finally:
                    # Drain tasks left by this SNMP call; leftover handle_timeout tasks
                    # would stop the loop before the next host's request completes.
                    _pending = asyncio.all_tasks(loop)
                    for _t in _pending:
                        _t.cancel()
                    if _pending:
                        loop.run_until_complete(asyncio.gather(*_pending, return_exceptions=True))

                try:
                    profile = check._profile_for_sysobject_oid(sys_object_oid)
                except ConfigurationError:
                    if not host_config.oid_config.has_oids():
                        check.log.warning("Host %s didn't match a profile for sysObjectID %s", host, sys_object_oid)
                        del check
                        continue
                else:
                    host_config.refresh_with_profile(check.profiles[profile])
                    host_config.add_profile_tag(profile)

                config.discovered_instances[host] = host_config

                write_persistent_cache(check.check_id, json.dumps(list(config.discovered_instances)))
                del check

            check = check_ref()
            if check is None:
                return
            # Write again at the end of the loop, in case some host have been removed since last
            write_persistent_cache(check.check_id, json.dumps(list(config.discovered_instances)))
            del check

            time_elapsed = time.time() - start_time
            if interval - time_elapsed > 0:
                time.sleep(interval - time_elapsed)
    finally:
        # Cancel pending pysnmp tasks and close the loop to release file descriptors.
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
        asyncio.set_event_loop(_prev_loop)
