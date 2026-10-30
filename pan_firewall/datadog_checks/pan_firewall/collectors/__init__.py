# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import counters, dataplane, ha, interfaces, licenses, reports, routing, rules, system, threats, vpn
from .base import Collector

# Every collector the poller schedules, by its name in `constants.INTERVALS`.
COLLECTORS: dict[str, Collector] = {
    'global_counters': counters.collect_global_counters,
    'dataplane': dataplane.collect_dataplane,
    'ha': ha.collect_ha,
    'interfaces': interfaces.collect_interfaces,
    'licenses': licenses.collect_licenses,
    'reports': reports.collect_reports,
    'bgp': routing.collect_bgp,
    'ospf': routing.collect_ospf,
    'rule_hits': rules.collect_rule_hits,
    'system_resources': system.collect_system_resources,
    'disk': system.collect_disk,
    'environment': system.collect_environment,
    'threats': threats.collect_threats,
    'vpn': vpn.collect_vpn,
}
