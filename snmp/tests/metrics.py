# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# Generic TCP metrics for routers
# _generic-router-tcp.yaml
TCP_COUNTS = [
    'tcpActiveOpens',
    'tcpPassiveOpens',
    'tcpAttemptFails',
    'tcpEstabResets',
    'tcpHCInSegs',
    'tcpHCOutSegs',
    'tcpRetransSegs',
    'tcpInErrs',
    'tcpOutRsts',
]
TCP_GAUGES = ['tcpCurrEstab']

# Generic UDP metrics for routers
# _generic-router-udp.yaml
UDP_COUNTS = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']

# Generic network interfaces metrics for routers.
# _generic-router-if.yaml
IF_COUNTS = ['ifInErrors', 'ifInDiscards', 'ifOutErrors', 'ifOutDiscards']
IFX_COUNTS = [
    'ifHCInOctets',
    'ifHCInUcastPkts',
    'ifHCInMulticastPkts',
    'ifHCInBroadcastPkts',
    'ifHCOutOctets',
    'ifHCOutUcastPkts',
    'ifHCOutMulticastPkts',
    'ifHCOutBroadcastPkts',
]
IF_RATES = [
    'ifHCInOctets.rate',
    'ifHCOutOctets.rate',
]
IF_GAUGES = ['ifAdminStatus', 'ifOperStatus', 'ifSpeed']

# Generic IP metrics for routers
# _generic-router-ip.yaml
IP_COUNTS = [
    'ipSystemStatsHCInReceives',
    'ipSystemStatsInHdrErrors',
    'ipSystemStatsOutFragReqds',
    'ipSystemStatsOutFragFails',
    'ipSystemStatsHCOutTransmits',
    'ipSystemStatsReasmReqds',
    'ipSystemStatsHCInMcastPkts',
    'ipSystemStatsReasmFails',
    'ipSystemStatsHCOutMcastPkts',
]
IPX_COUNTS = [
    'ipSystemStatsHCInOctets',
    'ipSystemStatsInNoRoutes',
    'ipSystemStatsInAddrErrors',
    'ipSystemStatsInUnknownProtos',
    'ipSystemStatsInTruncatedPkts',
    'ipSystemStatsHCInForwDatagrams',
    'ipSystemStatsReasmOKs',
    'ipSystemStatsInDiscards',
    'ipSystemStatsHCInDelivers',
    'ipSystemStatsHCOutRequests',
    'ipSystemStatsOutNoRoutes',
    'ipSystemStatsHCOutForwDatagrams',
    'ipSystemStatsOutDiscards',
    'ipSystemStatsOutFragOKs',
    'ipSystemStatsOutFragCreates',
    'ipSystemStatsHCOutOctets',
    'ipSystemStatsHCInMcastOctets',
    'ipSystemStatsHCOutMcastOctets',
    'ipSystemStatsHCInBcastPkts',
    'ipSystemStatsHCOutBcastPkts',
]
IP_IF_COUNTS = [
    'ipIfStatsHCInOctets',
    'ipIfStatsInHdrErrors',
    'ipIfStatsInNoRoutes',
    'ipIfStatsInAddrErrors',
    'ipIfStatsInUnknownProtos',
    'ipIfStatsInTruncatedPkts',
    'ipIfStatsHCInForwDatagrams',
    'ipIfStatsReasmReqds',
    'ipIfStatsReasmOKs',
    'ipIfStatsReasmFails',
    'ipIfStatsInDiscards',
    'ipIfStatsHCInDelivers',
    'ipIfStatsHCOutRequests',
    'ipIfStatsHCOutForwDatagrams',
    'ipIfStatsOutDiscards',
    'ipIfStatsOutFragReqds',
    'ipIfStatsOutFragOKs',
    'ipIfStatsOutFragFails',
    'ipIfStatsOutFragCreates',
    'ipIfStatsHCOutTransmits',
    'ipIfStatsHCOutOctets',
    'ipIfStatsHCInMcastPkts',
    'ipIfStatsHCInMcastOctets',
    'ipIfStatsHCOutMcastPkts',
    'ipIfStatsHCOutMcastOctets',
    'ipIfStatsHCInBcastPkts',
    'ipIfStatsHCOutBcastPkts',
]

# IDRAC profile metrics
# idrac.yaml
ADAPTER_IF_COUNTS = [
    'adapterRxPackets',
    'adapterTxPackets',
    'adapterRxBytes',
    'adapterTxBytes',
    'adapterRxErrors',
    'adapterTxErrors',
    'adapterRxDropped',
    'adapterTxDropped',
    'adapterRxMulticast',
    'adapterCollisions',
]
SYSTEM_STATUS_GAUGES = [
    'systemStateChassisStatus',
    'systemStatePowerUnitStatusRedundancy',
    'systemStatePowerSupplyStatusCombined',
    'systemStateAmperageStatusCombined',
    'systemStateCoolingUnitStatusRedundancy',
    'systemStateCoolingDeviceStatusCombined',
    'systemStateTemperatureStatusCombined',
    'systemStateMemoryDeviceStatusCombined',
    'systemStateChassisIntrusionStatusCombined',
    'systemStatePowerUnitStatusCombined',
    'systemStateCoolingUnitStatusCombined',
    'systemStateProcessorDeviceStatusCombined',
    'systemStateTemperatureStatisticsStatusCombined',
]
DISK_GAUGES = [
    'physicalDiskState',
    'physicalDiskCapacityInMB',
    'physicalDiskUsedSpaceInMB',
    'physicalDiskFreeSpaceInMB',
]

PROBE_GAUGES = ['amperageProbeReading', 'amperageProbeStatus']

VOLTAGE_GAUGES = ['voltageProbeStatus', 'voltageProbeReading']

DRS_GAUGES = [
    'drsCMCCurrStatus',
    'drsGlobalCurrStatus',
    'drsPowerCurrStatus',
    'drsRedCurrStatus',
    'drsGlobalSystemStatus',
]

# Base profile metrics for Cisco devices
# _base_cisco.yaml
FRU_METRICS = [
    "cefcFRUPowerAdminStatus",
    "cefcFRUPowerOperStatus",
    "cefcFRUCurrent",
]
CPU_METRICS = [
    "cpmCPUTotalMonIntervalValue",
    "cpmCPUMemoryUsed",
    "cpmCPUMemoryFree",
    "cpmCPUTotal1minRev",
]
CIE_METRICS = [
    "cieIfLastInTime",
    "cieIfLastOutTime",
    "cieIfInputQueueDrops",
    "cieIfOutputQueueDrops",
]
MEMORY_METRICS = [
    'ciscoMemoryPoolUsed',
    'ciscoMemoryPoolFree',
    'ciscoMemoryPoolLargestFree',
]

# F5-BIG-IP profile metrics.
# f5-big-ip.yaml

LTM_GAUGES = [
    'ltmVirtualServNumber',
    'ltmNodeAddrNumber',
    'ltmPoolNumber',
    'ltmPoolMemberNumber',
]

LTM_VIRTUAL_SERVER_GAUGES = [
    'ltmVirtualServEnabled',
    'ltmVirtualServConnLimit',
    'ltmVirtualServStatClientCurConns',
    'ltmVirtualServStatVsUsageRatio5s',
    'ltmVirtualServStatVsUsageRatio1m',
    'ltmVirtualServStatVsUsageRatio5m',
    'ltmVirtualServStatCurrentConnsPerSec',
    'ltmVirtualServStatDurationRateExceeded',
]

LTM_VIRTUAL_SERVER_COUNTS = [
    'ltmVirtualServStatNoNodesErrors',
    'ltmVirtualServStatClientTotConns',
    'ltmVirtualServStatClientEvictedConns',
    'ltmVirtualServStatClientSlowKilled',
    'ltmVirtualServStatTotRequests',
]

LTM_VIRTUAL_SERVER_RATES = [
    'ltmVirtualServStatClientPktsIn',
    'ltmVirtualServStatClientBytesIn',
    'ltmVirtualServStatClientPktsOut',
    'ltmVirtualServStatClientBytesOut',
]

LTM_NODES_GAUGES = [
    'ltmNodeAddrSessionStatus',
    'ltmNodeAddrConnLimit',
    'ltmNodeAddrRatio',
    'ltmNodeAddrDynamicRatio',
    'ltmNodeAddrMonitorState',
    'ltmNodeAddrMonitorStatus',
    'ltmNodeAddrStatServerCurConns',
    'ltmNodeAddrStatCurSessions',
    'ltmNodeAddrStatCurrentConnsPerSec',
    'ltmNodeAddrStatDurationRateExceeded',
]

LTM_NODES_COUNTS = [
    'ltmNodeAddrStatServerTotConns',
    'ltmNodeAddrStatTotRequests',
]

LTM_NODES_RATES = [
    'ltmNodeAddrStatServerPktsIn',
    'ltmNodeAddrStatServerBytesIn',
    'ltmNodeAddrStatServerPktsOut',
    'ltmNodeAddrStatServerBytesOut',
]

LTM_POOL_GAUGES = [
    'ltmPoolDynamicRatioSum',
    'ltmPoolMemberCnt',
    'ltmPoolActiveMemberCnt',
    'ltmPoolStatServerCurConns',
    'ltmPoolStatConnqDepth',
    'ltmPoolStatConnqAgeHead',
    'ltmPoolStatCurSessions',
]

LTM_POOL_COUNTS = [
    'ltmPoolStatServerTotConns',
    'ltmPoolStatConnqServiced',
    'ltmPoolStatTotRequests',
]

LTM_POOL_RATES = [
    'ltmPoolStatServerPktsIn',
    'ltmPoolStatServerBytesIn',
    'ltmPoolStatServerPktsOut',
    'ltmPoolStatServerBytesOut',
]

LTM_POOL_MEMBER_GAUGES = [
    'ltmPoolMemberMonitorState',
    'ltmPoolMemberMonitorStatus',
    'ltmPoolMemberSessionStatus',
    'ltmPoolMemberConnLimit',
    'ltmPoolMemberRatio',
    'ltmPoolMemberDynamicRatio',
    'ltmPoolMemberStatServerCurConns',
    'ltmPoolMemberStatConnqDepth',
    'ltmPoolMemberStatConnqAgeHead',
    'ltmPoolMemberStatCurSessions',
    'ltmPoolMemberStatCurrentConnsPerSec',
    'ltmPoolMemberStatDurationRateExceeded',
]

LTM_POOL_MEMBER_COUNTS = [
    'ltmPoolMemberStatServerTotConns',
    'ltmPoolMemberStatTotRequests',
    'ltmPoolMemberStatConnqServiced',
]

LTM_POOL_MEMBER_RATES = [
    'ltmPoolMemberStatServerPktsIn',
    'ltmPoolMemberStatServerBytesIn',
    'ltmPoolMemberStatServerPktsOut',
    'ltmPoolMemberStatServerBytesOut',

# Base profile metrics from BPG profile
# _generic-router-bgp4.yaml
PEER_GAUGES = [
    'bgpPeerAdminStatus',
    'bgpPeerNegotiatedVersion',
    'bgpPeerRemoteAs',
    'bgpPeerState',
    'bgpPeerFsmEstablishedTime',
    'bgpPeerConnectRetryInterval',
    'bgpPeerHoldTime',
    'bgpPeerKeepAlive',
    'bgpPeerHoldTimeConfigured',
    'bgpPeerKeepAliveConfigured',
    'bgpPeerMinASOriginationInterval',
]
PEER_RATES = [
    'bgpPeerInUpdates',
    'bgpPeerOutUpdates',
    'bgpPeerInTotalMessages',
    'bgpPeerOutTotalMessages',
    'bgpPeerFsmEstablishedTransitions',
]
