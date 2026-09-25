# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Collectors.

The device collector is the load-bearing one: a single `data/networkDevices` call returns
switches, routers, access points and controllers together, each carrying its own health scores,
its AP configuration and per-radio KPIs, and its fabric role. One paginated request therefore
covers what would otherwise be four separate per-device fan-outs.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from datadog_checks.base import AgentCheck

from .client import CatalystCenterClient
from .constants import (
    ASSURANCE_EVENTS_ENDPOINT,
    ASSURANCE_ISSUES_ENDPOINT,
    CLIENT_HEALTH_ENDPOINT,
    CLIENTS_SUMMARY_ANALYTICS_ENDPOINT,
    EVENT_DEFAULT_ALERT_TYPE,
    EVENT_DEFAULT_MAX_PAGES,
    EVENT_DETAIL_FIELDS,
    EVENT_DEVICE_FAMILY_GROUPS,
    EVENT_SEVERITY_ALERT_TYPES,
    EVENT_SOURCE_TYPE,
    EVENT_TAG_FIELDS,
    EVENT_TYPE,
    FABRIC_SITE_HEALTH_ENDPOINT,
    INTENT_INTERFACE_METADATA_FIELDS,
    INTENT_INTERFACES_ENDPOINT,
    INTERFACES_ENDPOINT,
    ISSUE_DEFAULT_ALERT_TYPE,
    ISSUE_DETAIL_FIELDS,
    ISSUE_EVENT_TYPE,
    ISSUE_PRIORITY_ALERT_TYPES,
    ISSUE_TAG_FIELDS,
    L3_TOPOLOGY_ENDPOINT_TEMPLATE,
    NETWORK_APPLICATIONS_ENDPOINT,
    NETWORK_DEVICES_ENDPOINT,
    NETWORK_HEALTH_ENDPOINT,
    PHYSICAL_TOPOLOGY_ENDPOINT,
    REACHABLE_VALUES,
    SECURITY_ROGUE_ENDPOINT,
    SECURITY_THREATS_ENDPOINT,
    SITE_HEALTH_SUMMARIES_ENDPOINT,
    SITE_TOPOLOGY_ENDPOINT,
    STACK_ENDPOINT_TEMPLATE,
    STACK_MEMBER_READY_STATES,
    STACK_PORT_OK_VALUES,
    STACKABLE_DEVICE_FAMILIES,
    UP_VALUES,
    VIRTUAL_NETWORK_HEALTH_ENDPOINT,
)
from .emit import compact, emit_gauge, emit_score, emit_watts, is_uplink, tag, to_number
from .errors import CatalystApiError
from .metrics import (
    APPLICATION_METRICS,
    CLIENT_AGGREGATES,
    CLIENT_GROUP_BY_DEFAULT,
    DEVICE_INTERFACE_LIST_METRICS,
    DEVICE_METRICS,
    DEVICE_METRICS_DETAILS,
    EVENT_BREAKDOWNS,
    FABRIC_SITE_METRICS,
    INTERFACE_POE_WATT_METRICS,
    INTERFACE_STATISTICS_METRICS,
    NETWORK_CATEGORY_METRICS,
    NETWORK_HEALTH_DISTRIBUTION_KEY,
    NETWORK_HEALTH_METRICS,
    RADIO_METRICS,
    SCORE_FIELDS,
    SITE_CLIENT_TYPES,
    SITE_DEVICE_FAMILIES,
    SITE_ISSUE_PRIORITIES,
    SITE_METRICS,
    VIRTUAL_NETWORK_METRICS,
)

KBPS_TO_BPS = 1000


DEFAULT_NAMESPACE = 'default'


def device_identity_tags(namespace: str, management_ip: Any, device_uuid: Any) -> list[str | None]:
    """The identity tags every device-scoped metric carries.

    `device_namespace`, `device_ip` and `device_id` are the NDM device record's `id_tags`, which
    NDM uses to correlate metrics with the device. `device_id` is the `{namespace}:{ip}` form the
    Agent's SNMP check also uses;
    `device_uuid` is Catalyst Center's own `instanceUuid`, which keys the NDM device record.
    Neither is derivable from the other: the UUID is stable and always present, the IP form is
    what correlates with SNMP.
    """
    return [
        tag('device_namespace', namespace),
        tag('device_ip', management_ip),
        tag('device_id', f'{namespace}:{management_ip}' if management_ip else None),
        tag('device_uuid', device_uuid),
    ]


def device_tags(record: dict[str, Any], namespace: str = DEFAULT_NAMESPACE) -> list[str]:
    """Tags shared by every metric derived from one device record."""
    return compact(
        [
            *device_identity_tags(namespace, record.get('managementIpAddress'), record.get('id')),
            tag('device_name', record.get('name')),
            tag('device_family', record.get('deviceFamily')),
            tag('device_series', record.get('deviceSeries')),
            tag('device_role', record.get('deviceRole')),
            tag('platform_id', record.get('platformId')),
            tag('os_type', record.get('osType')),
            tag('software_version', record.get('softwareVersion')),
            tag('site_id', record.get('siteId')),
            tag('site_hierarchy', record.get('siteHierarchy')),
            tag('reachability', record.get('reachabilityHealthStatus')),
        ]
    )


def _collect_radios(check: AgentCheck, record: dict[str, Any], base_tags: list[str]) -> None:
    """Emit per-radio KPIs from `apDetails.radios[]`.

    `apDetails` is null on every non-AP record and `radios` can be null on an AP that has not
    reported yet, so both are treated as absent rather than iterated.
    """
    ap_details = record.get('apDetails') or {}
    radios = ap_details.get('radios') or []

    ap_tags = base_tags + compact(
        [
            tag('ap_group', ap_details.get('apGroup')),
            tag('ap_mode', ap_details.get('operationalMode')),
            tag('wlc_name', ap_details.get('connectedWlcName')),
        ]
    )

    for radio in radios:
        radio_tags = ap_tags + compact(
            [
                tag('radio_slot', radio.get('slot')),
                tag('radio_band', radio.get('radioBand')),
            ]
        )
        for field, metric_name in RADIO_METRICS.items():
            emit_gauge(check, metric_name, radio.get(field), radio_tags)


def collect_devices(
    check: AgentCheck,
    client: CatalystCenterClient,
    collect_wireless: bool,
    base_tags: list[str] | None = None,
    namespace: str = DEFAULT_NAMESPACE,
) -> list[dict[str, Any]]:
    """Collect every managed device, returning the records so callers need not refetch them.

    The stack collector needs the device list to bound its fan-out, and this is the only call
    that produces it.

    Args:
        check: The check instance, used for metric submission.
        client: An authenticated `CatalystCenterClient`.
        collect_wireless: Whether to fan out into per-radio metrics. Off by default because the
            radio mapping is derived from Cisco's schema and has not been validated against a
            live controller.
        base_tags: Tags applied to every metric, carrying the instance's configured `tags`.
    """
    records = client.get_list(NETWORK_DEVICES_ENDPOINT)
    base_tags = base_tags or []

    for record in records:
        tags = base_tags + device_tags(record, namespace)

        # Reachability as a metric, not only as NDM inventory: a monitor cannot alert on
        # inventory, and "is this device up" is the first question an operator asks.
        reachability = record.get('reachabilityHealthStatus')
        if reachability is not None:
            check.gauge('device.reachable', int(reachability in REACHABLE_VALUES), tags=tags)

        for field, metric_name in DEVICE_METRICS.items():
            emit_gauge(check, metric_name, record.get(field), tags)

        metrics_details = record.get('metricsDetails') or {}
        for field, metric_name in DEVICE_METRICS_DETAILS.items():
            value = metrics_details.get(field)
            if field in SCORE_FIELDS:
                emit_score(check, metric_name, value, tags)
            else:
                emit_gauge(check, metric_name, value, tags)

        # An empty list is zero affected interfaces, not missing data, so it is counted rather
        # than skipped. `or []` guards the null the field carries before first collection.
        for field, metric_name in DEVICE_INTERFACE_LIST_METRICS.items():
            if field in metrics_details:
                check.gauge(metric_name, len(metrics_details[field] or []), tags=tags)

        if collect_wireless:
            _collect_radios(check, record, tags)

    return records


# -- interfaces -----------------------------------------------------------------------


def _uplink_tag_value(record: dict[str, Any]) -> str | None:
    """`true` for an uplink, `false` only where the appliance actually said so.

    An interface with no `isWan` and no matching description is unclassified, not known to be
    an access port, so it gets no tag at all. Emitting `uplink:false` there would assert
    something the data does not support -- the same mistake as emitting `0` for absent data.
    """
    if is_uplink(record):
        return 'true'
    return 'false' if record.get('isWan') is not None else None


def interface_tags(record: dict[str, Any], namespace: str = DEFAULT_NAMESPACE) -> list[str]:
    """Identity and configuration tags for one interface.

    Only the `configuration` view carries the descriptive fields, so the merged record is what
    should be passed here. See `_uplink_tag_value()` for when the `uplink` tag is omitted.
    """
    return compact(
        [
            *device_identity_tags(namespace, record.get('networkDeviceIpAddress'), record.get('networkDeviceId')),
            tag('interface', record.get('name')),
            tag('interface_type', record.get('interfaceType')),
            tag('admin_status', record.get('adminStatus')),
            tag('oper_status', record.get('operStatus')),
            tag('port_mode', record.get('portMode')),
            tag('duplex', record.get('duplexOper')),
            tag('media_type', record.get('mediaType')),
            tag('vlan', record.get('vlanId')),
            tag('uplink', _uplink_tag_value(record)),
            tag('site_hierarchy', record.get('siteHierarchy')),
        ]
    )


def _merge_views(client: CatalystCenterClient, views: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    """Fetch each view and merge the results into one record per interface id.

    A view replaces the field set rather than extending it, so the only way to see an
    interface's configuration and its throughput together is to ask twice and join. The join key
    is `id`; every view returns it. The views overlap only on identity fields, which they report
    identically, so the order they are merged in does not change the result.
    """
    merged: dict[str, dict[str, Any]] = {}
    for view in views:
        for record in client.get_list(INTERFACES_ENDPOINT, params={'view': view}):
            interface_id = record.get('id')
            if interface_id is None:
                continue
            merged.setdefault(interface_id, {}).update(record)
    return merged


def _enrich_metadata(client: CatalystCenterClient, merged: dict[str, dict[str, Any]]) -> None:
    """Fill the interface metadata fields the data API leaves null, from the intent API.

    Throughput, errors and PoE exist only on the data API; `macAddress` and `description` only on
    the intent API. The join is free: both identify an interface by the same UUID.

    Only `INTENT_INTERFACE_METADATA_FIELDS` is copied, and only where the intent record carries a
    value -- see the constant for why a wholesale merge is wrong. Interfaces the intent inventory
    omits, such as stack sub-interfaces, keep their data API record unchanged.
    """
    for record in client.get_list(INTENT_INTERFACES_ENDPOINT):
        interface_id = record.get('id')
        if interface_id is None:
            continue
        target = merged.get(interface_id)
        if target is None:
            continue
        for field in INTENT_INTERFACE_METADATA_FIELDS:
            value = record.get(field)
            if value not in (None, ''):
                target[field] = value


def collect_interfaces(
    check: AgentCheck,
    client: CatalystCenterClient,
    views: tuple[str, ...],
    base_tags: list[str] | None = None,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, dict[str, Any]]:
    """Collect port health, returning the merged records keyed by interface id.

    The records are returned rather than counted so that NDM metadata can be built from the same
    fetch instead of asking for every interface a second time.

    The intent API sweep is unconditional: it is the only source of `description`, which is the
    only uplink signal on hardware that leaves `isWan` null. Gating it on NDM would leave the
    uplink metrics and the `uplink` tag unreachable. It costs one more paginated pass.

    Args:
        check: The check instance.
        client: An authenticated client.
        views: Which interface views to request and join on the interface id.
        base_tags: Tags applied to every metric.
    """
    base_tags = base_tags or []
    merged = _merge_views(client, views)
    _enrich_metadata(client, merged)

    for record in merged.values():
        tags = base_tags + interface_tags(record, namespace)

        oper_status = record.get('operStatus')
        if oper_status is not None:
            check.gauge('interface.status', int(oper_status in UP_VALUES), tags=tags)

        admin_status = record.get('adminStatus')
        if admin_status is not None:
            check.gauge('interface.admin_status', int(admin_status in UP_VALUES), tags=tags)

        # `speed` is documented in Kbps and returned as a string. NDM and this metric are bps.
        # Coerced before scaling: multiplying first would raise on the absent-data shapes
        # emit_gauge exists to skip, losing every interface after this one.
        speed_kbps = to_number(record.get('speed'))
        if speed_kbps is not None:
            emit_gauge(check, 'interface.speed', speed_kbps * KBPS_TO_BPS, tags)

        for field, metric_name in INTERFACE_STATISTICS_METRICS.items():
            emit_gauge(check, metric_name, record.get(field), tags)

        for field, metric_name in INTERFACE_POE_WATT_METRICS.items():
            emit_watts(check, metric_name, record.get(field), tags)

    _emit_device_rollups(check, merged.values(), base_tags, namespace)

    return merged


@dataclass
class _DeviceThroughput:
    """Per-device accumulator for `_emit_device_rollups`.

    `uplinks` is a count and `seen` is a flag; neither is a rate, unlike the other four fields.
    """

    rx: float = 0.0
    tx: float = 0.0
    uplink_rx: float = 0.0
    uplink_tx: float = 0.0
    uplinks: int = 0
    seen: bool = False
    device_uuid: str | None = None


def _emit_device_rollups(
    check: AgentCheck, records: Iterable[dict[str, Any]], base_tags: list[str], namespace: str
) -> None:
    """Roll per-interface rates up to per-device and per-uplink totals.

    Device-level and uplink-level throughput are both sums over interfaces, and rolling them up
    here means a dashboard does not have to.

    Which interfaces count as uplinks is `is_uplink()`'s decision, so this aggregate,
    the `uplink` tag and the NDM port role cannot drift apart. `portMode` is deliberately not
    part of that rule: it would relabel every trunk port as an uplink, which on an access switch
    is most of them.
    """
    totals: dict[str, _DeviceThroughput] = {}

    for record in records:
        device_ip = record.get('networkDeviceIpAddress')
        if not device_ip:
            continue
        bucket = totals.setdefault(device_ip, _DeviceThroughput())
        if not bucket.device_uuid:
            bucket.device_uuid = record.get('networkDeviceId') or None

        # to_number, not float(): the statistics view is absent for some interfaces and the
        # appliance spells absence several ways. A bare float() turns `{}` or `''` into a 0 that
        # emit_gauge suppressed at the per-interface level, and raises on any other non-numeric.
        rx, tx = to_number(record.get('rxRate')), to_number(record.get('txRate'))
        if rx is None and tx is None:
            # No statistics for this interface; it contributes nothing to a throughput sum.
            continue
        bucket.seen = True
        bucket.rx += rx or 0.0
        bucket.tx += tx or 0.0

        if is_uplink(record):
            bucket.uplinks += 1
            bucket.uplink_rx += rx or 0.0
            bucket.uplink_tx += tx or 0.0

    for device_ip, bucket in totals.items():
        if not bucket.seen:
            continue
        tags = base_tags + compact(device_identity_tags(namespace, device_ip, bucket.device_uuid))
        check.gauge('device.throughput.rx', bucket.rx, tags=tags)
        check.gauge('device.throughput.tx', bucket.tx, tags=tags)

        if bucket.uplinks:
            check.gauge('device.uplink.count', bucket.uplinks, tags=tags)
            check.gauge('device.uplink.throughput.rx', bucket.uplink_rx, tags=tags)
            check.gauge('device.uplink.throughput.tx', bucket.uplink_tx, tags=tags)


# -- site health ----------------------------------------------------------------------


def site_tags(record: dict[str, Any]) -> list[str]:
    """Identity tags for one site.

    There is no `siteName` field, so the name is the leaf of `siteHierarchy`. Names are not
    unique -- the sandbox alone has two sites that collide -- so `site_id` is the identity and
    `site_name` is for display.
    """
    hierarchy = (record.get('siteHierarchy') or '').strip()
    parts = [segment for segment in hierarchy.split('/') if segment]
    return compact(
        [
            tag('site_id', record.get('id')),
            tag('site_name', parts[-1] if parts else None),
            tag('parent_site_name', parts[-2] if len(parts) > 1 else None),
            tag('site_type', record.get('siteType')),
            tag('site_hierarchy', hierarchy or None),
        ]
    )


def list_sites(client: CatalystCenterClient) -> list[dict[str, Any]]:
    """List the site hierarchy.

    Separate from `collect_site_health` because application health needs a site on every request
    but the user may have site metrics switched off.
    """
    return client.get_list(SITE_HEALTH_SUMMARIES_ENDPOINT)


def collect_site_health(
    check: AgentCheck, client: CatalystCenterClient, base_tags: list[str] | None = None
) -> list[dict[str, Any]]:
    """Collect per-site rollups, returning the site records.

    The records are returned because application health needs a site on every request, and this
    is the only call that enumerates them.
    """
    base_tags = base_tags or []
    records = list_sites(client)

    for record in records:
        tags = base_tags + site_tags(record)

        for field, metric_name in SITE_METRICS.items():
            emit_gauge(check, metric_name, record.get(field), tags)

        # Device counts repeat the same shape once per family, so the family is a tag.
        for family in SITE_DEVICE_FAMILIES:
            family_tags = tags + [f'device_family:{family}']
            emit_gauge(check, 'site.device.count', record.get(f'{family}DeviceCount'), family_tags)
            emit_gauge(check, 'site.device.health.count', record.get(f'{family}DeviceGoodHealthCount'), family_tags)
            emit_gauge(
                check,
                'site.device.health.percentage',
                record.get(f'{family}DeviceGoodHealthPercentage'),
                family_tags,
            )

        for client_type in SITE_CLIENT_TYPES:
            client_tags = tags + [f'client_type:{client_type}']
            emit_gauge(check, 'site.client.count', record.get(f'{client_type}ClientCount'), client_tags)
            emit_gauge(
                check,
                'site.client.health.count',
                record.get(f'{client_type}ClientGoodHealthCount'),
                client_tags,
            )
            emit_gauge(
                check,
                'site.client.health.percentage',
                record.get(f'{client_type}ClientGoodHealthPercentage'),
                client_tags,
            )

        for priority in SITE_ISSUE_PRIORITIES:
            emit_gauge(check, 'site.issue.count', record.get(f'{priority}IssueCount'), tags + [f'priority:{priority}'])

    return records


# -- network health -------------------------------------------------------------------


def collect_network_health(check: AgentCheck, client: CatalystCenterClient, base_tags: list[str] | None = None) -> None:
    """Collect the global rollup.

    Everything of interest is a top-level sibling of `response`; `response` itself is a
    time-bucketed array. Reading `response[0].healthScore` would pick an arbitrary bucket and
    look correct for as long as the bucket and the latest score happen to agree.
    """
    tags = base_tags or []
    body = client.get_envelope(NETWORK_HEALTH_ENDPOINT)

    for field, metric_name in NETWORK_HEALTH_METRICS.items():
        emit_gauge(check, metric_name, body.get(field), tags)

    for category in body.get(NETWORK_HEALTH_DISTRIBUTION_KEY) or []:
        category_tags = tags + compact([tag('category', category.get('category'))])
        for field, metric_name in NETWORK_CATEGORY_METRICS.items():
            emit_gauge(check, metric_name, category.get(field), category_tags)


# -- switch stacks --------------------------------------------------------------------


def collect_stacks(
    check: AgentCheck,
    client: CatalystCenterClient,
    devices: list[dict[str, Any]],
    base_tags: list[str] | None = None,
    namespace: str = DEFAULT_NAMESPACE,
) -> None:
    """Collect stack membership.

    The only per-device fan-out in the check, so it is bounded to stackable families and off by
    default. Stack membership changes on human timescales, so a large fleet should run this on a
    second instance with a long `min_collection_interval`. Caching instead would be wrong:
    `member.state` and `port.status` are fault signals, and re-emitting a stale `1` reports a
    healthy stack that is not.

    A device that fails is logged and skipped: one unreachable switch must not cost the cycle.
    """
    base_tags = base_tags or []

    for device in devices:
        if device.get('deviceFamily') not in STACKABLE_DEVICE_FAMILIES:
            continue

        device_id = device.get('id')
        if device_id is None:
            continue

        tags = base_tags + compact(
            [
                *device_identity_tags(namespace, device.get('managementIpAddress'), device_id),
                tag('device_name', device.get('name')),
            ]
        )

        try:
            stack = client.get_object(STACK_ENDPOINT_TEMPLATE.format(device_id=device_id))
        except CatalystApiError:
            check.log.warning('Could not read stack detail for device %s', device_id, exc_info=True)
            continue

        # Both of these are null rather than empty on a device with no stack, so `or []` is
        # load-bearing: iterating None raises TypeError on the first real payload.
        members = stack.get('stackSwitchInfo') or []
        check.gauge('device.stack.member.count', len(members), tags=tags)

        for member in members:
            member_tags = tags + compact(
                [
                    tag('stack_member', member.get('stackMemberNumber')),
                    tag('stack_role', member.get('role')),
                    tag('stack_mac', member.get('macAddress')),
                ]
            )
            state = member.get('state')
            if state is not None:
                check.gauge('device.stack.member.state', int(state in STACK_MEMBER_READY_STATES), tags=member_tags)
            emit_gauge(check, 'device.stack.member.priority', member.get('switchPriority'), member_tags)

        for port in stack.get('stackPortInfo') or []:
            port_tags = tags + compact([tag('stack_port', port.get('name'))])
            sync_ok = port.get('isSynchOk')
            if sync_ok is not None:
                check.gauge('device.stack.port.status', int(str(sync_ok) in STACK_PORT_OK_VALUES), tags=port_tags)


# -- aggregate client health ------------------------------------------------------------


def collect_client_health(check: AgentCheck, client: CatalystCenterClient, base_tags: list[str] | None = None) -> None:
    """Collect the org-level client score distribution.

    One bulk call, no per-client fan-out. `scoreValue` is `-1` when Catalyst Center has no
    client data, so it goes through `emit_score()` while the counts do not -- a client count
    of zero is a real measurement.
    """
    base_tags = base_tags or []

    for site in client.get_list(CLIENT_HEALTH_ENDPOINT):
        site_tags = base_tags + compact([tag('site_id', site.get('siteId'))])

        for detail in site.get('scoreDetail') or []:
            category = detail.get('scoreCategory') or {}
            tags = site_tags + compact([tag('client_type', category.get('value'))])

            emit_score(check, 'client.health', detail.get('scoreValue'), tags)
            emit_gauge(check, 'client.count', detail.get('clientCount'), tags)
            emit_gauge(check, 'client.unique.count', detail.get('clientUniqueCount'), tags)


# -- client experience ----------------------------------------------------------------


def _emit_aggregates(check: AgentCheck, aggregates: list[dict[str, Any]] | None, tags: list[str]) -> None:
    """Emit one metric per requested (field, function) pair.

    A requested aggregate can come back with `value: null` when the underlying field has no
    data, which `emit_gauge()` drops.
    """
    by_key = {(a.get('name'), a.get('function')): a.get('value') for a in aggregates or []}
    for field, function, metric_name in CLIENT_AGGREGATES:
        emit_gauge(check, metric_name, by_key.get((field, function)), tags)


def collect_client_experience(
    check: AgentCheck,
    client: CatalystCenterClient,
    group_by: tuple[str, ...] = CLIENT_GROUP_BY_DEFAULT,
    base_tags: list[str] | None = None,
) -> None:
    """Collect client signal quality and onboarding timings, aggregated by the appliance.

    One POST, no per-client fan-out and no client MAC in the tag set. See
    `CLIENT_AGGREGATES` for why the aggregation happens server-side.

    Every slot in the response -- `attributes`, `aggregateAttributes`, `groups` -- is
    `null` rather than empty when there is no client data, so each is guarded.
    """
    base_tags = base_tags or []
    body = {
        'groupBy': list(group_by),
        'aggregateAttributes': [{'name': field, 'function': function} for field, function, _ in CLIENT_AGGREGATES],
    }

    summary = client.post_object(CLIENTS_SUMMARY_ANALYTICS_ENDPOINT, body=body)

    # Ungrouped totals, present when the appliance returns them alongside or instead of groups.
    _emit_aggregates(check, summary.get('aggregateAttributes'), base_tags)

    for group in summary.get('groups') or []:
        group_tags = base_tags + compact(
            [tag(attr.get('name'), attr.get('value')) for attr in group.get('attributes') or []]
        )
        _emit_aggregates(check, group.get('aggregateAttributes'), group_tags)


# -- topology -------------------------------------------------------------------------


def collect_topology(check: AgentCheck, client: CatalystCenterClient, base_tags: list[str] | None = None) -> None:
    """Collect the CDP/LLDP-derived physical topology and emit link status.

    `source` and `target` on each link are device UUIDs, the same id NDM device metadata uses.

    This endpoint is not paginated. A large fabric returns every link in one response, so treat
    it as a single large read rather than a cheap one.
    """
    tags = base_tags or []
    topology = client.get_object(PHYSICAL_TOPOLOGY_ENDPOINT)

    links = topology.get('links') or []
    check.gauge('topology.link.count', len(links), tags=tags)

    for link in links:
        status = link.get('linkStatus')
        if status is None:
            continue
        link_tags = tags + compact(
            [
                tag('source_device_uuid', link.get('source')),
                tag('target_device_uuid', link.get('target')),
                tag('source_interface', link.get('startPortName')),
                tag('target_interface', link.get('endPortName')),
            ]
        )
        check.gauge('topology.link.status', int(status in UP_VALUES), tags=link_tags)


def collect_site_topology(check: AgentCheck, client: CatalystCenterClient, base_tags: list[str] | None = None) -> None:
    """Collect the size of the site hierarchy.

    Device-to-site mapping already rides on every device record as `siteId` and `siteHierarchy`,
    so the only thing left to report here is the size of the hierarchy itself.
    """
    tags = base_tags or []
    topology = client.get_object(SITE_TOPOLOGY_ENDPOINT)
    check.gauge('topology.site.count', len(topology.get('sites') or []), tags=tags)


def collect_l3_topology(
    check: AgentCheck, client: CatalystCenterClient, topology_type: str, base_tags: list[str] | None = None
) -> None:
    """Collect the L3 routing graph size for one topology type.

    Only counts are emitted; the graph itself is not submitted anywhere by this integration.
    `L3_TOPOLOGY_TYPES` lists the types the endpoint serves.
    """
    tags = (base_tags or []) + [f'topology_type:{topology_type}']
    topology = client.get_object(L3_TOPOLOGY_ENDPOINT_TEMPLATE.format(topology_type=topology_type))
    check.gauge('topology.l3.link.count', len(topology.get('links') or []), tags=tags)
    check.gauge('topology.l3.node.count', len(topology.get('nodes') or []), tags=tags)


# -- SD-Access fabric -----------------------------------------------------------------


def collect_sda_fabric(
    check: AgentCheck, client: CatalystCenterClient, devices: list[dict[str, Any]], base_tags: list[str] | None = None
) -> None:
    """Collect fabric health and node roles.

    `sda/edge-device` and `sda/border-device` answer 400 with no list mode, so node roles cannot
    be read from them in bulk. `fabricDetails` on the bulk device record carries the same
    information at no extra cost, so roles are counted from records already in hand.
    """
    tags = base_tags or []

    # Casing is inconsistent in the API's own examples (['Border', 'edge']), so normalise it
    # rather than emit two tags for one role.
    role_counts = Counter(
        str(role).lower() for device in devices for role in (device.get('fabricDetails') or {}).get('fabricRole') or []
    )

    for role, count in sorted(role_counts.items()):
        check.gauge('fabric.device.count', count, tags=tags + [f'fabric_role:{role}'])

    for site in client.get_list(FABRIC_SITE_HEALTH_ENDPOINT):
        site_tags = tags + compact([tag('fabric_site_id', site.get('id')), tag('fabric_site_name', site.get('name'))])
        for field, metric_name in FABRIC_SITE_METRICS.items():
            emit_gauge(check, metric_name, site.get(field), site_tags)

    for vn in client.get_list(VIRTUAL_NETWORK_HEALTH_ENDPOINT):
        vn_tags = tags + compact([tag('virtual_network', vn.get('name')), tag('vn_layer', vn.get('layer'))])
        for field, metric_name in VIRTUAL_NETWORK_METRICS.items():
            emit_gauge(check, metric_name, vn.get(field), vn_tags)


# -- assurance issues -----------------------------------------------------------------


def _group_counts(records: list[dict[str, Any]], fields: Sequence[tuple[str, str]]) -> dict[tuple[str, ...], int]:
    """Count `records` by the tags they carry across `fields`, one entry per distinct tag set.

    Each record is counted once, carrying all of its breakdown tags at the same time, so the counts
    sum to the number of records however they are grouped or filtered. A breakdown per field under
    one metric name would count every record once per field instead. A value the record does not
    carry is left out of its tag set rather than filled with a placeholder, matching `tag()`.
    """
    counts = Counter(
        tuple(compact([tag(tag_key, record.get(field)) for field, tag_key in fields])) for record in records
    )
    return dict(sorted(counts.items()))


def _count_by(
    submit: Callable[..., None],
    metric_name: str,
    records: list[dict[str, Any]],
    fields: Sequence[tuple[str, str]],
    tags: list[str],
) -> None:
    """Submit a breakdown of `records` across `fields`, one series per distinct tag set."""
    for breakdown_tags, count in _group_counts(records, fields).items():
        submit(metric_name, count, tags=tags + list(breakdown_tags))


def _issue_alert_type(record: dict[str, Any]) -> str:
    """Map a Catalyst Center issue priority onto a Datadog alert type.

    P1 is the most severe, the inverse of the syslog scale `_event_alert_type()` reads. An
    unrecognised or absent value becomes `info` rather than `error`.
    """
    priority = record.get('priority')
    if not isinstance(priority, str):
        return ISSUE_DEFAULT_ALERT_TYPE
    return ISSUE_PRIORITY_ALERT_TYPES.get(priority, ISSUE_DEFAULT_ALERT_TYPE)


def _issue_body(record: dict[str, Any]) -> str:
    """Assemble the diagnosis text, skipping fields the appliance left empty.

    Every field is rendered as free text. The published schema names `suggestedActions` without
    giving its type, so a structured value would need handling here.
    """
    return '\n'.join(f'{label}: {record[field]}' for field, label in ISSUE_DETAIL_FIELDS if record.get(field))


def _issue_payload(record: dict[str, Any], base_tags: list[str]) -> dict[str, Any]:
    """Build one Datadog event from one assurance issue record.

    `host` is left unset for the same reason as assurance events: a Catalyst Center device name
    is not a Datadog hostname. `aggregation_key` is the appliance's own issue id, so the
    successive occurrences of one long-lived issue collapse into a single thread.
    """
    occurred = record.get('mostRecentOccurredTime')
    payload: dict[str, Any] = {
        'event_type': ISSUE_EVENT_TYPE,
        'source_type_name': EVENT_SOURCE_TYPE,
        'msg_title': str(record.get('name') or 'Catalyst Center assurance issue'),
        'msg_text': _issue_body(record),
        'alert_type': _issue_alert_type(record),
        'tags': base_tags + [f'{tag_key}:{record[field]}' for field, tag_key in ISSUE_TAG_FIELDS if record.get(field)],
    }
    if isinstance(occurred, int):
        # The appliance reports epoch milliseconds; the events intake expects seconds.
        payload['timestamp'] = occurred // 1000
    if record.get('issueId'):
        payload['aggregation_key'] = str(record['issueId'])
    return payload


def _is_new_occurrence(reported: dict[str, int | None], issue_id: str, occurred: int | None) -> bool:
    """Whether an issue has not been reported yet, or has recurred since it was."""
    if issue_id not in reported:
        return True
    previous = reported[issue_id]
    return occurred is not None and previous is not None and occurred > previous


def collect_assurance_issues(
    check: AgentCheck,
    client: CatalystCenterClient,
    base_tags: list[str] | None = None,
    reported: dict[str, int | None] | None = None,
) -> dict[str, int | None]:
    """Collect open issues as counts, and newly-occurring ones as Datadog events.

    Returns each current issue's `mostRecentOccurredTime` keyed by `issueId`, which the caller
    stores and hands back as `reported` on the next cycle. On the first cycle `reported` is None
    and every current issue is reported.

    Counts and events are deliberately asymmetric. Every open issue is counted on every cycle,
    because counts describe current state. An issue stays open until it clears, so one event per
    cycle would turn a single unresolved problem into an unbounded stream. An issue is therefore
    reported when its id is new, or when it recurs with a later `mostRecentOccurredTime`. Keying
    on the id rather than on the newest time seen means an issue that surfaces after a newer one
    is still reported, and one with no timestamp is reported once. The state is rebuilt from the
    current list, so it never outgrows the open issues.

    `suggestedActions` arrives in this same response, so no separate `issue-enrichment-details`
    call is needed. It is free text, so the event body is where it lands.
    """
    tags = base_tags or []
    issues = client.get_list(ASSURANCE_ISSUES_ENDPOINT)

    # Zero open issues is the healthy steady state and a real measurement, so it is always
    # emitted rather than left as a gap in the graph.
    check.gauge('issue.total.count', len(issues), tags=tags)

    _count_by(check.gauge, 'issue.count', issues, ISSUE_TAG_FIELDS, tags)

    current: dict[str, int | None] = {}
    for record in issues:
        if record.get('issueId') is None:
            # Nothing to recognise it by on the next cycle, so it is counted but not reported.
            continue
        issue_id = str(record['issueId'])
        occurred = record.get('mostRecentOccurredTime')
        occurred = occurred if isinstance(occurred, int) else None
        current[issue_id] = occurred
        if reported is None or _is_new_occurrence(reported, issue_id, occurred):
            check.event(_issue_payload(record, tags))

    return current


# -- assurance events -----------------------------------------------------------------


def _event_alert_type(record: dict[str, Any]) -> str:
    """Map a Catalyst Center syslog severity onto a Datadog alert type.

    Severity 0 is the most severe. An unrecognised or absent value becomes `info` rather than
    `error`, so a scale change on the appliance cannot manufacture alerts.
    """
    severity = record.get('severity')
    if not isinstance(severity, int):
        return EVENT_DEFAULT_ALERT_TYPE
    return EVENT_SEVERITY_ALERT_TYPES.get(severity, EVENT_DEFAULT_ALERT_TYPE)


def _event_body(record: dict[str, Any]) -> str:
    """Assemble the diagnosis text, skipping fields the appliance left empty.

    These are the fields the metric breakdown cannot carry: free text, and several of them
    per-client. Here they are searchable without becoming tag dimensions.
    """
    lines = [f'{label}: {record[field]}' for field, label in EVENT_DETAIL_FIELDS if record.get(field)]
    for field, label in (('networkDeviceName', 'Device'), ('clientMac', 'Client MAC'), ('username', 'Username')):
        if record.get(field):
            lines.append(f'{label}: {record[field]}')
    return '\n'.join(lines)


def _event_payload(record: dict[str, Any], fallback_timestamp: int, base_tags: list[str]) -> dict[str, Any]:
    """Build one Datadog event from one assurance event record.

    `host` is deliberately left unset. Catalyst Center device names are not Datadog hostnames, and
    setting one that does not resolve invents a host in the infrastructure list; the device is
    carried as a tag and in the body instead.

    `aggregation_key` is the appliance's own event id, which is what lets the stream collapse the
    duplicates a re-polled window produces.
    """
    timestamp = record.get('timestamp')
    payload: dict[str, Any] = {
        # The appliance reports epoch milliseconds; the events intake expects seconds.
        'timestamp': int(timestamp) // 1000 if isinstance(timestamp, int) else fallback_timestamp,
        'event_type': EVENT_TYPE,
        'source_type_name': EVENT_SOURCE_TYPE,
        'msg_title': str(record.get('name') or 'Catalyst Center assurance event'),
        'msg_text': _event_body(record),
        'alert_type': _event_alert_type(record),
        'tags': base_tags + compact([tag(tag_key, record.get(field)) for field, tag_key in EVENT_TAG_FIELDS]),
    }
    if record.get('id'):
        payload['aggregation_key'] = str(record['id'])
    return payload


def collect_events(
    check: AgentCheck,
    client: CatalystCenterClient,
    start_time: int,
    end_time: int,
    base_tags: list[str] | None = None,
) -> None:
    """Collect assurance events in one time window, as Datadog events plus aggregate counts.

    Each record becomes a Datadog event carrying the diagnosis, and the same records are counted
    with their severity, family, type and device as tags. Both are submitted because they answer different
    questions: the counts are what a monitor alerts on, the events are what someone reads
    afterwards to find out why.

    This is the fallback ingestion path. Where outbound webhooks are permitted, an Event
    Management subscription posts the same events straight to the Datadog intake and this
    collector should stay disabled; running both submits every event twice.

    The window is supplied rather than derived here so the caller owns the cursor -- consecutive
    windows must not overlap. Both bounds are epoch milliseconds.

    Four requests is the floor: `deviceFamily` is mandatory and its values fall into four groups
    the endpoint refuses to mix, so each group is its own sweep (`EVENT_DEVICE_FAMILY_GROUPS`).
    A failing group is logged and skipped, costing one window of its events; failing the whole
    collection instead would have the caller retry and double-count the groups that succeeded.
    If *every* group fails there is nothing to double-count, so that case raises and the window is
    retried next cycle.

    `event.total.count` comes from the total the appliance reports rather than from the records
    that arrived, so it survives a sweep cut short by the page budget. The breakdown cannot, so a
    truncated sweep is warned about loudly.
    """
    tags = base_tags or []
    window = {'startTime': start_time, 'endTime': end_time}
    any_group_succeeded = False

    for group in EVENT_DEVICE_FAMILY_GROUPS:
        try:
            # `deviceFamily` is serialised as a repeated query parameter, which is the only form
            # the endpoint accepts for more than one family; a comma-separated string is rejected.
            records, total = client.get_list_with_total(
                ASSURANCE_EVENTS_ENDPOINT,
                params={'deviceFamily': list(group), **window},
                max_pages=EVENT_DEFAULT_MAX_PAGES,
            )
        except CatalystApiError:
            check.log.warning('Could not read assurance events for %s', ', '.join(group), exc_info=True)
            continue

        any_group_succeeded = True

        # Untagged, and submitted once per group. Counts sharing a name and tag set are summed,
        # so the four submissions add up to the whole window. The group is an artefact of the
        # endpoint's parameter rules, not a dimension anyone queries -- `event.count` already
        # carries the finer-grained `device_family` breakdown.
        reported = total if total is not None else len(records)
        check.count('event.total.count', reported, tags=tags)

        if reported > len(records):
            check.log.warning(
                'Catalyst Center reports %s assurance events for %s but only %s were read within '
                'the page budget; the event.count breakdown undercounts this window',
                reported,
                ', '.join(group),
                len(records),
            )

        _count_by(check.count, 'event.count', records, EVENT_BREAKDOWNS, tags)

        # A record with no timestamp falls back to the end of the window it was found in, which is
        # the latest moment it could have happened.
        fallback_timestamp = end_time // 1000
        for record in records:
            check.event(_event_payload(record, fallback_timestamp, tags))

    if not any_group_succeeded:
        raise CatalystApiError(
            f'Could not read assurance events for any device family group in window {start_time}-{end_time}'
        )


# -- application visibility -----------------------------------------------------------


def collect_application_health(
    check: AgentCheck, client: CatalystCenterClient, sites: list[dict[str, Any]], base_tags: list[str] | None = None
) -> None:
    """Collect health and traffic for the busiest applications at each site, one call per site.

    `siteId` is mandatory here -- omitting it returns `errorCode 14029`, whose message reads
    `siteIds` while the accepted parameter is singular. So this is a genuine per-site fan-out
    whose cost scales with the hierarchy, which is why it is gated off by default.

    A site that fails is logged and skipped rather than aborting the sweep.
    """
    tags = base_tags or []

    for site in sites:
        site_id = site.get('id')
        if site_id is None:
            continue

        site_tags = tags + compact([tag('site_id', site_id), tag('site_hierarchy', site.get('siteHierarchy'))])
        try:
            # There is no top-N endpoint. Sorting descending by usage and reading one page is how
            # to get the busiest applications, and keeps the series bounded however many a site
            # runs. `order` accepts only `asc` or `desc`.
            applications = client.get_first_page(
                NETWORK_APPLICATIONS_ENDPOINT,
                params={'siteId': site_id, 'sortBy': 'usage', 'order': 'desc'},
            )
        except CatalystApiError:
            check.log.warning('Could not read application health for site %s', site_id, exc_info=True)
            continue

        for application in applications:
            app_tags = site_tags + compact(
                [
                    tag('application', application.get('name')),
                    tag('traffic_class', application.get('trafficClass')),
                    tag('ssid', application.get('ssid')),
                ]
            )
            for field, metric_name in APPLICATION_METRICS.items():
                emit_gauge(check, metric_name, application.get(field), app_tags)


# -- security -------------------------------------------------------------------------


def collect_security(check: AgentCheck, client: CatalystCenterClient, base_tags: list[str] | None = None) -> None:
    """Collect rogue device and aWIPS threat counts.

    Both are wireless-edge features, so both report nothing on a wired-only deployment. Zero is
    emitted rather than skipped: "no rogues detected" is the answer the metric exists to give.
    """
    tags = base_tags or []

    rogues = client.get_list(SECURITY_ROGUE_ENDPOINT)
    check.gauge('security.rogue.total.count', len(rogues), tags=tags)
    _count_by(check.gauge, 'security.rogue.count', rogues, [('threatLevel', 'threat_level')], tags)

    threats = client.get_list(SECURITY_THREATS_ENDPOINT)
    check.gauge('security.threat.total.count', len(threats), tags=tags)
    _count_by(check.gauge, 'security.threat.count', threats, [('threatType', 'threat_type')], tags)
