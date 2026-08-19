# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Collectors.

One module while there are two of them. It splits when the third arrives.

The device collector is the load-bearing one: a single ``data/networkDevices`` call returns
switches, routers, access points and controllers together, each carrying its own health scores,
its AP configuration and per-radio KPIs, and its fabric role. What the product brief describes as
four separate per-device fan-outs is one paginated request.
"""

from __future__ import annotations

from typing import Any

from .constants import (
    ASSURANCE_EVENTS_ENDPOINT,
    ASSURANCE_ISSUES_ENDPOINT,
    CLIENT_HEALTH_ENDPOINT,
    CLIENTS_SUMMARY_ANALYTICS_ENDPOINT,
    DEVICE_REACHABLE_VALUES,
    EVENT_DEFAULT_MAX_PAGES,
    EVENT_DEVICE_FAMILY_GROUPS,
    FABRIC_SITE_HEALTH_ENDPOINT,
    INTERFACES_ENDPOINT,
    L3_TOPOLOGY_ENDPOINT_TEMPLATE,
    NETWORK_APPLICATIONS_ENDPOINT,
    NETWORK_DEVICES_ENDPOINT,
    NETWORK_HEALTH_ENDPOINT,
    PHYSICAL_TOPOLOGY_ENDPOINT,
    SECURITY_ROGUE_ENDPOINT,
    SECURITY_THREATS_ENDPOINT,
    SITE_HEALTH_SUMMARIES_ENDPOINT,
    SITE_TOPOLOGY_ENDPOINT,
    STACK_ENDPOINT_TEMPLATE,
    STACK_MEMBER_READY_STATES,
    STACK_PORT_OK_VALUES,
    STACKABLE_DEVICE_FAMILIES,
    TOPOLOGY_LINK_UP_VALUES,
    VIRTUAL_NETWORK_HEALTH_ENDPOINT,
)
from .emit import compact, emit_gauge, emit_score, emit_watts, tag
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
    INTERFACE_UP_STATES,
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
    """The two identity tags every device-scoped metric carries.

    ``device_id`` is the ``{namespace}:{ip}`` form the Agent's SNMP check also uses, so one tag
    key means one thing across both halves of the pairing. ``device_uuid`` carries Catalyst
    Center's own ``instanceUuid``, which is what the NDM device record is keyed on.

    Both are emitted because they answer different questions and neither is derivable from the
    other: the UUID is stable and always present, the IP form is what correlates with SNMP.
    """
    return [
        tag('device_id', f'{namespace}:{management_ip}' if management_ip else None),
        tag('device_uuid', device_uuid),
    ]


def device_tags(record: dict[str, Any], namespace: str = DEFAULT_NAMESPACE) -> list[str]:
    """Tags shared by every metric derived from one device record."""
    return compact(
        [
            *device_identity_tags(namespace, record.get('managementIpAddress'), record.get('id')),
            tag('device_name', record.get('name')),
            tag('device_ip', record.get('managementIpAddress')),
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


def _collect_radios(check: Any, record: dict[str, Any], base_tags: list[str]) -> None:
    """Emit per-radio KPIs from ``apDetails.radios[]``.

    ``apDetails`` is null on every non-AP record and ``radios`` can be null on an AP that has not
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
    check: Any,
    client: Any,
    collect_wireless: bool,
    base_tags: list[str] | None = None,
    namespace: str = DEFAULT_NAMESPACE,
) -> list[dict[str, Any]]:
    """Collect every managed device, returning the records so callers need not refetch them.

    The stack collector needs the device list to bound its fan-out, and this is the only call
    that produces it.

    Args:
        check: The check instance, used for metric submission.
        client: An authenticated :class:`~.client.CatalystCenterClient`.
        collect_wireless: Whether to fan out into per-radio metrics. Off by default because the
            radio mapping is derived from Cisco's schema and has not been validated against a
            live controller.
        base_tags: Tags applied to every metric, carrying the instance's configured ``tags``.
    """
    records = client.get_list(NETWORK_DEVICES_ENDPOINT)
    base_tags = base_tags or []

    for record in records:
        tags = base_tags + device_tags(record, namespace)

        # "Is this device up" is the first question an operator asks. It was previously only in
        # the NDM payload, which is inventory rather than something you can alert on.
        reachability = record.get('reachabilityHealthStatus')
        if reachability is not None:
            check.gauge('device.reachable', int(reachability in DEVICE_REACHABLE_VALUES), tags=tags)

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


def interface_tags(record: dict[str, Any], namespace: str = DEFAULT_NAMESPACE) -> list[str]:
    """Identity and configuration tags for one interface.

    Only the ``configuration`` view carries the descriptive fields, so the merged record is what
    should be passed here. ``isWan`` is null on hardware that does not report it, and :func:`tag`
    drops it rather than emitting ``uplink:None``.
    """
    return compact(
        [
            *device_identity_tags(namespace, record.get('networkDeviceIpAddress'), record.get('networkDeviceId')),
            tag('device_ip', record.get('networkDeviceIpAddress')),
            tag('interface', record.get('name')),
            tag('interface_type', record.get('interfaceType')),
            tag('admin_status', record.get('adminStatus')),
            tag('oper_status', record.get('operStatus')),
            tag('port_mode', record.get('portMode')),
            tag('duplex', record.get('duplexOper')),
            tag('media_type', record.get('mediaType')),
            tag('vlan', record.get('vlanId')),
            tag('uplink', str(record['isWan']).lower() if record.get('isWan') is not None else None),
            tag('site_hierarchy', record.get('siteHierarchy')),
        ]
    )


def _merge_views(client: Any, views: tuple[str, ...], max_pages_guard: str) -> dict[str, dict[str, Any]]:
    """Fetch each view and merge the results into one record per interface id.

    A view replaces the field set rather than extending it, so the only way to see an
    interface's configuration and its throughput together is to ask twice and join. The join key
    is ``id``; every view returns it.
    """
    merged: dict[str, dict[str, Any]] = {}
    for view in views:
        for record in client.get_list(INTERFACES_ENDPOINT, params={'view': view}):
            interface_id = record.get('id')
            if interface_id is None:
                continue
            merged.setdefault(interface_id, {}).update(record)
    return merged


def collect_interfaces(
    check: Any,
    client: Any,
    views: tuple[str, ...],
    base_tags: list[str] | None = None,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, dict[str, Any]]:
    """Collect port health, returning the merged records keyed by interface id.

    The records are returned rather than counted so that NDM metadata can be built from the same
    fetch instead of asking for every interface a second time.

    Args:
        check: The check instance.
        client: An authenticated client.
        views: Which interface views to request, in merge order. ``configuration`` should come
            first so that later views cannot overwrite the descriptive fields.
        base_tags: Tags applied to every metric.
    """
    base_tags = base_tags or []
    merged = _merge_views(client, views, INTERFACES_ENDPOINT)

    for record in merged.values():
        tags = base_tags + interface_tags(record, namespace)

        oper_status = record.get('operStatus')
        if oper_status is not None:
            check.gauge('interface.status', int(oper_status in INTERFACE_UP_STATES), tags=tags)

        admin_status = record.get('adminStatus')
        if admin_status is not None:
            check.gauge('interface.admin_status', int(admin_status in INTERFACE_UP_STATES), tags=tags)

        # `speed` is documented in Kbps and returned as a string. NDM and this metric are bps.
        speed_kbps = record.get('speed')
        if speed_kbps not in (None, ''):
            emit_gauge(check, 'interface.speed', float(speed_kbps) * KBPS_TO_BPS, tags)

        for field, metric_name in INTERFACE_STATISTICS_METRICS.items():
            emit_gauge(check, metric_name, record.get(field), tags)

        for field, metric_name in INTERFACE_POE_WATT_METRICS.items():
            emit_watts(check, metric_name, record.get(field), tags)

    _emit_device_rollups(check, merged.values(), base_tags, namespace)

    return merged


def _emit_device_rollups(check: Any, records: Any, base_tags: list[str], namespace: str) -> None:
    """Roll per-interface rates up to per-device and per-uplink totals.

    The brief asks for device-level throughput and for aggregate uplink throughput. Both are sums
    over interfaces, and doing them here means a dashboard does not have to.

    Only interfaces the appliance has actually flagged via ``isWan`` count as uplinks. Guessing
    from ``portMode`` would silently relabel every trunk port as an uplink, which on an access
    switch is most of them.
    """
    totals: dict[str, dict[str, float]] = {}

    for record in records:
        device_ip = record.get('networkDeviceIpAddress')
        if not device_ip:
            continue
        bucket = totals.setdefault(
            device_ip,
            {'rx': 0.0, 'tx': 0.0, 'uplink_rx': 0.0, 'uplink_tx': 0.0, 'uplinks': 0.0, 'seen': 0.0},
        )

        rx, tx = record.get('rxRate'), record.get('txRate')
        if rx is None and tx is None:
            # No statistics view for this interface; it contributes nothing to a throughput sum.
            continue
        bucket['seen'] = 1.0
        bucket['rx'] += float(rx or 0)
        bucket['tx'] += float(tx or 0)

        if record.get('isWan'):
            bucket['uplinks'] += 1
            bucket['uplink_rx'] += float(rx or 0)
            bucket['uplink_tx'] += float(tx or 0)

    for device_ip, bucket in totals.items():
        if not bucket['seen']:
            continue
        tags = base_tags + compact([*device_identity_tags(namespace, device_ip, None), tag('device_ip', device_ip)])
        check.gauge('device.throughput.rx', bucket['rx'], tags=tags)
        check.gauge('device.throughput.tx', bucket['tx'], tags=tags)

        if bucket['uplinks']:
            check.gauge('device.uplink.count', bucket['uplinks'], tags=tags)
            check.gauge('device.uplink.throughput.rx', bucket['uplink_rx'], tags=tags)
            check.gauge('device.uplink.throughput.tx', bucket['uplink_tx'], tags=tags)


# -- site health ----------------------------------------------------------------------


def site_tags(record: dict[str, Any]) -> list[str]:
    """Identity tags for one site.

    There is no ``siteName`` field, so the name is the leaf of ``siteHierarchy``. Names are not
    unique -- the sandbox alone has two sites that collide -- so ``site_id`` is the identity and
    ``site_name`` is for display.
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


def collect_site_health(check: Any, client: Any, base_tags: list[str] | None = None) -> list[dict[str, Any]]:
    """Collect per-site rollups, returning the site records.

    The records are returned because application health needs a site on every request, and this
    is the only call that enumerates them.
    """
    base_tags = base_tags or []
    records = client.get_list(SITE_HEALTH_SUMMARIES_ENDPOINT)

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


def collect_network_health(check: Any, client: Any, base_tags: list[str] | None = None) -> None:
    """Collect the global rollup.

    Everything of interest is a top-level sibling of ``response``; ``response`` itself is a
    time-bucketed array. Reading ``response[0].healthScore`` would pick an arbitrary bucket and
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
    check: Any,
    client: Any,
    devices: list[dict[str, Any]],
    base_tags: list[str] | None = None,
    namespace: str = DEFAULT_NAMESPACE,
) -> int:
    """Collect stack membership, returning how many devices were queried.

    This is the only per-device fan-out in the P0 set, so it is bounded to stackable families
    rather than issued for every managed device. Stack membership changes on human timescales,
    which is why the caller is expected to run it on a longer interval than the health cycle.

    A device that fails is logged and skipped: one unreachable switch must not cost the whole
    cycle.
    """
    base_tags = base_tags or []
    queried = 0

    for device in devices:
        if device.get('deviceFamily') not in STACKABLE_DEVICE_FAMILIES:
            continue

        device_id = device.get('id')
        if device_id is None:
            continue

        queried += 1
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

    return queried


# -- aggregate client health ------------------------------------------------------------


def collect_client_health(check: Any, client: Any, base_tags: list[str] | None = None) -> None:
    """Collect the org-level client score distribution.

    One bulk call, no per-client fan-out. ``scoreValue`` is ``-1`` when Catalyst Center has no
    client data, so it goes through :func:`emit_score` while the counts do not -- a client count
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


def _emit_aggregates(check: Any, aggregates: list[dict[str, Any]] | None, tags: list[str]) -> None:
    """Emit one metric per requested (field, function) pair.

    A requested aggregate can come back with ``value: null`` when the underlying field has no
    data, which :func:`emit_gauge` drops.
    """
    by_key = {(a.get('name'), a.get('function')): a.get('value') for a in aggregates or []}
    for field, function, metric_name in CLIENT_AGGREGATES:
        emit_gauge(check, metric_name, by_key.get((field, function)), tags)


def collect_client_experience(
    check: Any,
    client: Any,
    group_by: tuple[str, ...] = CLIENT_GROUP_BY_DEFAULT,
    base_tags: list[str] | None = None,
) -> None:
    """Collect client signal quality and onboarding timings, aggregated by the appliance.

    One POST, no per-client fan-out and no client MAC in the tag set. See
    :data:`~.metrics.CLIENT_AGGREGATES` for why the aggregation happens server-side.

    Every slot in the response -- ``attributes``, ``aggregateAttributes``, ``groups`` -- is
    ``null`` rather than empty when there is no client data, so each is guarded.
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


def collect_topology(check: Any, client: Any, base_tags: list[str] | None = None) -> dict[str, Any]:
    """Collect the CDP/LLDP-derived physical topology, returning it for NDM link building.

    ``source`` and ``target`` on each link are device UUIDs, which is what the NDM device record
    is keyed on, so links resolve to devices without a translation step.

    This endpoint is not paginated. A large fabric returns every link in one response, so treat
    it as a single large read rather than a cheap one.
    """
    tags = base_tags or []
    topology = client.get_object(PHYSICAL_TOPOLOGY_ENDPOINT)

    links = topology.get('links') or []
    nodes = topology.get('nodes') or []
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
        check.gauge('topology.link.status', int(status in TOPOLOGY_LINK_UP_VALUES), tags=link_tags)

    return {'links': links, 'nodes': nodes}


def collect_site_topology(check: Any, client: Any, base_tags: list[str] | None = None) -> None:
    """Collect the size of the site hierarchy.

    The brief asks for site topology as hierarchy plus device-to-site mapping. The mapping already
    rides on every device record as ``siteId`` and ``siteHierarchy``, so this contributes only the
    hierarchy size.
    """
    tags = base_tags or []
    topology = client.get_object(SITE_TOPOLOGY_ENDPOINT)
    check.gauge('topology.site.count', len(topology.get('sites') or []), tags=tags)


def collect_l3_topology(check: Any, client: Any, topology_type: str, base_tags: list[str] | None = None) -> None:
    """Collect the L3 routing graph size for one topology type.

    The brief names OSPF, IS-IS and static. Only counts are emitted: the graph itself belongs in
    NDM topology links rather than in metrics, and the physical topology already supplies those.
    """
    tags = (base_tags or []) + [f'topology_type:{topology_type}']
    topology = client.get_object(L3_TOPOLOGY_ENDPOINT_TEMPLATE.format(topology_type=topology_type))
    check.gauge('topology.l3.link.count', len(topology.get('links') or []), tags=tags)
    check.gauge('topology.l3.node.count', len(topology.get('nodes') or []), tags=tags)


# -- SD-Access fabric -----------------------------------------------------------------


def collect_sda_fabric(
    check: Any, client: Any, devices: list[dict[str, Any]], base_tags: list[str] | None = None
) -> None:
    """Collect fabric health and node roles.

    The brief routes node status through ``sda/edge-device`` and ``sda/border-device``, which
    answer 400 with no list mode. ``fabricDetails`` on the bulk device record carries the same
    information at no extra cost, so roles are counted from records already in hand.
    """
    tags = base_tags or []

    role_counts: dict[str, int] = {}
    for device in devices:
        fabric = device.get('fabricDetails') or {}
        # Casing is inconsistent in the API's own examples (['Border', 'edge']), so normalise it
        # rather than emit two tags for one role.
        for role in fabric.get('fabricRole') or []:
            normalized = str(role).lower()
            role_counts[normalized] = role_counts.get(normalized, 0) + 1

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


def _group_counts(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    """Count ``records`` by the value of one field, in sorted key order.

    Records whose value is absent are skipped rather than grouped under a placeholder. Both of
    Catalyst Center's absent-data conventions for a string count as absent, matching
    :func:`~.emit.tag`: an empty tag value is never a useful dimension to query on.
    """
    counts: dict[str, int] = {}
    for record in records:
        value = record.get(field)
        if value is None or value == '':
            continue
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


def _count_by(
    check: Any, metric_name: str, records: list[dict[str, Any]], field: str, tag_key: str, tags: list[str]
) -> None:
    """Emit a per-value breakdown of ``records`` grouped on one field."""
    for value, count in _group_counts(records, field).items():
        check.gauge(metric_name, count, tags=tags + [f'{tag_key}:{value}'])


def collect_assurance_issues(check: Any, client: Any, base_tags: list[str] | None = None) -> None:
    """Collect open assurance issues as counts by severity, priority, category and status.

    ``suggestedActions`` arrives in this same response, so the brief's separate
    ``issue-enrichment-details`` call is unnecessary. Turning individual issues into Datadog
    events is the ingestion decision the brief leaves open, and is deliberately not done here.
    """
    tags = base_tags or []
    issues = client.get_list(ASSURANCE_ISSUES_ENDPOINT)

    # Zero open issues is the healthy steady state and a real measurement, so it is always
    # emitted rather than left as a gap in the graph.
    check.gauge('issue.total.count', len(issues), tags=tags)

    for field, tag_key in (
        ('severity', 'severity'),
        ('priority', 'priority'),
        ('category', 'category'),
        ('status', 'status'),
    ):
        _count_by(check, 'issue.count', issues, field, tag_key, tags)


# -- assurance events -----------------------------------------------------------------


def collect_events(
    check: Any,
    client: Any,
    start_time: int,
    end_time: int,
    base_tags: list[str] | None = None,
) -> None:
    """Collect assurance events in one time window, as counts by severity, family, type and device.

    The window is supplied rather than derived here so that the caller owns the cursor: consecutive
    windows must not overlap, or every event is counted more than once. Both bounds are epoch
    milliseconds.

    Four requests is the floor. ``deviceFamily`` is mandatory, and its values fall into four groups
    the endpoint refuses to mix, so each group is its own sweep -- see
    :data:`EVENT_DEVICE_FAMILY_GROUPS`.

    A group that fails is logged and skipped rather than aborting the sweep. That costs one window
    of that group's events, which is the lesser of two evils: the alternative is to fail the whole
    collection so the caller retries the window, which would double-count everything the groups
    before it already submitted.

    ``event.total.count`` comes from the total the appliance reports, not from the records that
    arrived, so it stays correct when a sweep is cut short by the page budget. The breakdown cannot
    be -- it is derived from records -- so a truncated sweep is warned about loudly.
    """
    tags = base_tags or []
    window = {'startTime': start_time, 'endTime': end_time}

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

        for field, tag_key in EVENT_BREAKDOWNS:
            for value, count in _group_counts(records, field).items():
                check.count('event.count', count, tags=tags + [f'{tag_key}:{value}'])


# -- application visibility -----------------------------------------------------------


def collect_application_health(
    check: Any, client: Any, sites: list[dict[str, Any]], base_tags: list[str] | None = None
) -> None:
    """Collect per-application health and traffic, one call per site.

    ``siteId`` is mandatory here -- omitting it returns ``errorCode 14029``, whose message reads
    ``siteIds`` while the accepted parameter is singular. So this is a genuine per-site fan-out
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
            # Sorting descending by usage is what makes this the brief's "top applications by
            # usage" -- there is no separate top-N endpoint, only this ordering.
            applications = client.get_list(
                NETWORK_APPLICATIONS_ENDPOINT,
                params={'siteId': site_id, 'sortBy': 'usage', 'order': 'des'},
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


def collect_security(check: Any, client: Any, base_tags: list[str] | None = None) -> None:
    """Collect rogue device and aWIPS threat counts.

    Both are wireless-edge features, so both report nothing on a wired-only deployment. Zero is
    emitted rather than skipped: "no rogues detected" is the answer the metric exists to give.
    """
    tags = base_tags or []

    rogues = client.get_list(SECURITY_ROGUE_ENDPOINT)
    check.gauge('security.rogue.count', len(rogues), tags=tags)
    _count_by(check, 'security.rogue.count', rogues, 'threatLevel', 'threat_level', tags)

    threats = client.get_list(SECURITY_THREATS_ENDPOINT)
    check.gauge('security.threat.count', len(threats), tags=tags)
    _count_by(check, 'security.threat.count', threats, 'threatType', 'threat_type', tags)
