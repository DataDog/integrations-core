# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Field-to-metric-name tables.

Flat dictionaries, not a declarative spec object. Adding wireless means adding a table, and
anything that needs real branching stays as explicit code in the collector.
"""

from __future__ import annotations

from typing import Final

# CommonDetails, on every device record regardless of family.
DEVICE_METRICS: Final[dict[str, str]] = {
    'clientCount': 'device.client.count',
    'wiredClientCount': 'device.client.wired.count',
    'wirelessClientCount': 'device.client.wireless.count',
    'portCount': 'device.port.count',
    'upTime': 'device.uptime',
}

# MetricsDetails. Scores are 1-10 composites and use -1 for "no data"; utilizations are
# percentages; the pool and timer fields are wireless-controller resource counters.
DEVICE_METRICS_DETAILS: Final[dict[str, str]] = {
    'overallHealthScore': 'device.health',
    'overallFabricScore': 'device.fabric.health',
    'cpuUtilization': 'device.cpu.utilization',
    'cpuScore': 'device.cpu.score',
    'memoryUtilization': 'device.memory.utilization',
    'memoryScore': 'device.memory.score',
    'avgTemperature': 'device.temperature.avg',
    'maxTemperature': 'device.temperature.max',
    'discardScore': 'device.link.discard.score',
    'errorScore': 'device.link.error.score',
    'interDeviceLinkScore': 'device.interdevice_link.score',
    'linkUtilizationScore': 'device.link.utilization.score',
    'wanLinkUtilization': 'device.wan_link.utilization',
    'freeTimer': 'device.free_timer',
    'freeTimerScore': 'device.free_timer.score',
    'packetPool': 'device.packet_pool',
    'packetPoolScore': 'device.packet_pool.score',
    'freeMemoryBuffer': 'device.free_memory_buffer',
    'freeMemoryBufferScore': 'device.free_memory_buffer.score',
    'wqePool': 'device.wqe_pool',
    'wqePoolScore': 'device.wqe_pool.score',
    'apCount': 'device.ap.count',
    'noiseScore': 'device.noise.score',
    'utilizationScore': 'device.utilization.score',
    'interferenceScore': 'device.interference.score',
    'airQualityScore': 'device.air_quality.score',
}

# MetricsDetails fields holding a list of interface names. An empty list means zero affected
# interfaces, which is a real measurement rather than missing data, so these are counted at the
# call site instead of being skipped as sentinels.
DEVICE_INTERFACE_LIST_METRICS: Final[dict[str, str]] = {
    'errorInterfaces': 'device.link.error.count',
    'discardInterfaces': 'device.link.discard.count',
    'interDeviceConnectedDownInterfaces': 'device.interdevice_link.down.count',
    'highLinkUtilizationInterfaces': 'device.link.high_utilization.count',
}

# RadioKpi, nested under apDetails.radios[]. noise is dBm; the rest are percentages except
# clientCount.
RADIO_METRICS: Final[dict[str, str]] = {
    'noise': 'device.ap.radio.noise',
    'airQuality': 'device.ap.radio.air_quality',
    'interference': 'device.ap.radio.interference',
    'trafficUtil': 'device.ap.radio.traffic_utilization',
    'utilization': 'device.ap.radio.utilization',
    'clientCount': 'device.ap.radio.client.count',
}

# InterfaceData, `view=statistics`. Rates are bits per second; the error, discard and
# utilization fields are percentages despite their names reading like counters.
INTERFACE_STATISTICS_METRICS: Final[dict[str, str]] = {
    'rxRate': 'interface.rx.rate',
    'txRate': 'interface.tx.rate',
    'rxError': 'interface.rx.error',
    'txError': 'interface.tx.error',
    'rxDiscards': 'interface.rx.discard',
    'txDiscards': 'interface.tx.discard',
    'rxUtilization': 'interface.rx.utilization',
    'txUtilization': 'interface.tx.utilization',
}

# InterfaceData, `view=poE`. Every value arrives as a string with the unit appended, e.g.
# "10.5W", so these are parsed rather than cast.
INTERFACE_POE_WATT_METRICS: Final[dict[str, str]] = {
    'pdPowerConsumedInWatt': 'interface.poe.power_consumed',
    'pdPowerBudgetInWatt': 'interface.poe.power_budget',
    'pdPowerRemainingInWatt': 'interface.poe.power_remaining',
    'pdPowerAdminMaxInWatt': 'interface.poe.power_admin_max',
    'pdMaxPowerDrawn': 'interface.poe.power_max_drawn',
}

# Values Catalyst Center uses for an interface that is up. Everything else counts as down, so a
# state the appliance invents later reads as down rather than crashing or reading as healthy.
INTERFACE_UP_STATES: Final[frozenset[str]] = frozenset({'UP', 'up'})

# siteHealthSummaries. Device counts are reported per family with a shared naming shape --
# `<family>DeviceCount` / `<family>DeviceGoodHealthCount` -- so the family becomes a tag rather
# than being baked into the metric name.
SITE_DEVICE_FAMILIES: Final[tuple[str, ...]] = (
    'access',
    'core',
    'distribution',
    'router',
    'switch',
    'wireless',
    'ap',
    'wlc',
)

SITE_CLIENT_TYPES: Final[tuple[str, ...]] = ('wired', 'wireless')

SITE_METRICS: Final[dict[str, str]] = {
    'networkDeviceCount': 'site.device.total.count',
    'networkDeviceGoodHealthCount': 'site.device.total.health.count',
    'networkDeviceGoodHealthPercentage': 'site.network.health',
    'clientCount': 'site.client.total.count',
    'clientGoodHealthCount': 'site.client.total.health.count',
    'clientDataUsage': 'site.client.data_usage',
    'issueCount': 'site.issue.total.count',
}

SITE_ISSUE_PRIORITIES: Final[tuple[str, ...]] = ('p1', 'p2', 'p3', 'p4')

# intent/network-health. Everything here is a top-level sibling of `response`, not inside it.
NETWORK_HEALTH_METRICS: Final[dict[str, str]] = {
    'latestHealthScore': 'network.health',
    'totalDevices': 'network.device.total.count',
    'monitoredDevices': 'network.device.monitored.count',
    'monitoredHealthyDevices': 'network.device.healthy.count',
    'monitoredFairHealthDevices': 'network.device.fair.count',
    'monitoredPoorHealthDevices': 'network.device.poor.count',
    'monitoredUnHealthyDevices': 'network.device.unhealthy.count',
    'noHealthDevices': 'network.device.no_health.count',
    'notApplicableDevices': 'network.device.not_applicable.count',
    'healthContributingDevices': 'network.device.contributing.count',
}

# Per-category rollup, under the misspelled key the API actually returns.
NETWORK_HEALTH_DISTRIBUTION_KEY: Final = 'healthDistirubution'
NETWORK_CATEGORY_METRICS: Final[dict[str, str]] = {
    'healthScore': 'network.category.health',
    'totalCount': 'network.category.device.count',
    'goodCount': 'network.category.device.good.count',
    'fairCount': 'network.category.device.fair.count',
    'badCount': 'network.category.device.bad.count',
    'noHealthCount': 'network.category.device.no_health.count',
}

# Fields where -1 means "not measured" rather than a real negative reading. Confined to this set
# so that a genuinely negative gauge -- radio noise in dBm, for one -- cannot inherit a filter it
# never opted into. `wanLinkUtilization` is listed explicitly because it carries the sentinel
# without a name a convention would catch.
SCORE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        'overallHealthScore',
        'overallFabricScore',
        'cpuScore',
        'memoryScore',
        'discardScore',
        'errorScore',
        'interDeviceLinkScore',
        'linkUtilizationScore',
        'freeTimerScore',
        'packetPoolScore',
        'freeMemoryBufferScore',
        'wqePoolScore',
        'noiseScore',
        'utilizationScore',
        'interferenceScore',
        'airQualityScore',
        'wanLinkUtilization',
    }
)

# FabricSiteSummary and VirtualNetworkSummary. Both schemas are large (82 and 59 fields) and
# almost entirely `<kpi><Good|Fair|Poor>HealthDeviceCount` variations, so only the top-level
# rollups are mapped; the per-KPI breakdowns can be added once a real fabric is available to
# confirm which of them populate.
FABRIC_SITE_METRICS: Final[dict[str, str]] = {
    'goodHealthPercentage': 'fabric.site.health',
    'totalDeviceCount': 'fabric.site.device.count',
    'goodHealthDeviceCount': 'fabric.site.device.good.count',
    'fairHealthDeviceCount': 'fabric.site.device.fair.count',
    'poorHealthDeviceCount': 'fabric.site.device.poor.count',
    'associatedL2VnCount': 'fabric.site.l2vn.count',
    'associatedL3VnCount': 'fabric.site.l3vn.count',
    'connectivityGoodHealthPercentage': 'fabric.site.connectivity.health',
    'controlPlaneGoodHealthPercentage': 'fabric.site.control_plane.health',
    'infraHealthyPercentage': 'fabric.site.infra.health',
}

VIRTUAL_NETWORK_METRICS: Final[dict[str, str]] = {
    'goodHealthPercentage': 'fabric.vn.health',
    'totalDeviceCount': 'fabric.vn.device.count',
    'goodHealthDeviceCount': 'fabric.vn.device.good.count',
    'totalEndpoints': 'fabric.vn.endpoint.count',
    'totalFabricSites': 'fabric.vn.fabric_site.count',
    'vnStatusHealthPercentage': 'fabric.vn.status.health',
    'bgpPeerGoodHealthPercentage': 'fabric.vn.bgp_peer.health',
    'vnServicesHealthPercentage': 'fabric.vn.services.health',
}

# NetworkApplicationCommonDetail. Latency fields are milliseconds, throughput is bits per second
# and usage is bytes.
APPLICATION_METRICS: Final[dict[str, str]] = {
    'healthScore': 'application.health',
    'usage': 'application.usage',
    'throughput': 'application.throughput',
    'packetLossPercent': 'application.packet_loss',
    'jitter': 'application.jitter',
    'networkLatency': 'application.latency.network',
    'clientNetworkLatency': 'application.latency.client',
    'serverNetworkLatency': 'application.latency.server',
    'applicationServerLatency': 'application.latency.server_app',
}

# Client experience, via POST clients/summaryAnalytics. Each entry is
# (field, aggregate function, metric name), and the *request* is built from this same tuple -- so
# what is asked for and what is parsed cannot drift apart.
#
# Aggregating on the appliance is deliberate. The brief asks for RSSI and SNR "per client", but a
# series per client would put client MAC in the tag set: tens of thousands of series at the scale
# of the named accounts, for a question nobody asks one client at a time. Grouping by SSID and
# band answers "which SSID is bad on which band" at a cardinality that stays bounded.
CLIENT_AGGREGATES: Final[tuple[tuple[str, str, str], ...]] = (
    ('rssi', 'avg', 'client.rssi.avg'),
    ('snr', 'avg', 'client.snr.avg'),
    ('dataRate', 'avg', 'client.data_rate.avg'),
    ('usage', 'sum', 'client.usage'),
    ('avgRunDuration', 'avg', 'client.onboarding.duration'),
    ('maxRunDuration', 'max', 'client.onboarding.duration.max'),
    ('avgAssocDuration', 'avg', 'client.onboarding.assoc.duration'),
    ('avgAuthDuration', 'avg', 'client.onboarding.auth.duration'),
    ('avgDhcpDuration', 'avg', 'client.onboarding.dhcp.duration'),
    ('macAddress', 'count', 'client.observed.count'),
)

# Which dimensions the appliance groups by. Only these eleven are accepted; notably `authType`
# and `connectionStatus` are not among them, so counts by connection state or authentication type
# are not obtainable this way.
CLIENT_GROUP_BY_DEFAULT: Final[tuple[str, ...]] = ('ssid', 'band')

# Client-experience metric names, needed by the metadata.csv coupling test since the table
# above is keyed by (field, function) rather than by metric name.
CLIENT_AGGREGATE_METRIC_NAMES: Final[frozenset[str]] = frozenset(name for _, _, name in CLIENT_AGGREGATES)

# Metrics emitted by explicit code rather than by iterating a table above: derived counts,
# boolean-to-integer mappings, and the per-family and per-type fan-outs whose names are built
# from a shared shape. Listed here so the metadata.csv coupling test has one place to look.
DERIVED_METRIC_NAMES: Final[frozenset[str]] = frozenset(
    {
        'device.count',
        'device.stack.member.count',
        'device.stack.member.state',
        'device.stack.member.priority',
        'device.stack.port.status',
        'interface.status',
        'interface.admin_status',
        'interface.speed',
        'site.device.count',
        'site.device.health.count',
        'site.device.health.percentage',
        'site.client.count',
        'site.client.health.count',
        'site.client.health.percentage',
        'site.issue.count',
        'client.health',
        'client.count',
        'client.unique.count',
        'topology.link.count',
        'topology.link.status',
        'topology.site.count',
        'fabric.device.count',
        'issue.total.count',
        'issue.count',
        'security.rogue.count',
        'security.threat.count',
        'device.reachable',
        'device.throughput.rx',
        'device.throughput.tx',
        'device.uplink.count',
        'device.uplink.throughput.rx',
        'device.uplink.throughput.tx',
        'topology.l3.link.count',
        'topology.l3.node.count',
    }
)

# Numeric values the API returns as strings.
STRING_NUMERIC_FIELDS: Final[frozenset[str]] = frozenset({'speed', 'ifIndex', 'interfaceIfIndex'})
