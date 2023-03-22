# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

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
