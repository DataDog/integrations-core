# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# Generic TCP metrics for routers
# _generic-tcp.yaml
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
# _generic-udp.yaml
UDP_COUNTS = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']

# Generic network interfaces metrics for routers.
# _generic-if.yaml
IF_COUNTS = [
    'ifInErrors',
    'ifInDiscards',
    'ifOutErrors',
    'ifOutDiscards',
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
    'ifInErrors.rate',
    'ifInDiscards.rate',
    'ifOutErrors.rate',
    'ifOutDiscards.rate',
]
IF_SCALAR_GAUGE = ['ifNumber']
IF_GAUGES = ['ifAdminStatus', 'ifOperStatus', 'ifSpeed', 'ifHighSpeed']
IF_BANDWIDTH_USAGE = ['ifBandwidthInUsage.rate', 'ifBandwidthOutUsage.rate']

# Generic IP metrics for routers
# _generic-ip.yaml
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
# _idrac.yaml
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
IDRAC_SYSTEM_STATUS_GAUGES = [
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

# Dell Poweredge
# dell-poweredge.yaml
POWEREDGE_SYSTEM_STATUS_GAUGES = [
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
]


# Base profile metrics from BPG profile
# _generic-bgp4.yaml
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

# Base profile metrics for Cisco voice
CCCA_ROUTER_GAUGES = [
    "cccaRouterAgentsLoggedOn",
    "cccaRouterCallsInProgress",
    "cccaRouterCallsInQueue",
]

# Juniper enterprise metrics

VIRTUAL_CHASSIS_COUNTS = [
    'jnxVirtualChassisPortInPkts',
    'jnxVirtualChassisPortOutPkts',
    'jnxVirtualChassisPortInOctets',
    'jnxVirtualChassisPortOutOctets',
    'jnxVirtualChassisPortInMcasts',
    'jnxVirtualChassisPortOutMcasts',
    'jnxVirtualChassisPortCarrierTrans',
    'jnxVirtualChassisPortInCRCAlignErrors',
    'jnxVirtualChassisPortUndersizePkts',
    'jnxVirtualChassisPortCollisions',
]

VIRTUAL_CHASSIS_RATES = [
    'jnxVirtualChassisPortInPkts1secRate',
    'jnxVirtualChassisPortOutPkts1secRate',
    'jnxVirtualChassisPortOutOctets1secRate',
    'jnxVirtualChassisPortInOctets1secRate',
]

COS_COUNTS = [
    'jnxCosIfsetQstatQedPkts',
    'jnxCosIfsetQstatQedBytes',
    'jnxCosIfsetQstatTxedPkts',
    'jnxCosIfsetQstatTxedBytes',
    'jnxCosIfsetQstatTailDropPkts',
    'jnxCosIfsetQstatTotalRedDropPkts',
    'jnxCosIfsetQstatLpNonTcpRedDropPkts',
    'jnxCosIfsetQstatLpTcpRedDropPkts',
    'jnxCosIfsetQstatHpNonTcpRedDropPkts',
    'jnxCosIfsetQstatHpTcpRedDropPkts',
    'jnxCosIfsetQstatTotalRedDropBytes',
    'jnxCosIfsetQstatLpNonTcpRedDropBytes',
    'jnxCosIfsetQstatLpTcpRedDropBytes',
    'jnxCosIfsetQstatHpNonTcpRedDropBytes',
    'jnxCosIfsetQstatHpTcpRedDropBytes',
    'jnxCosIfsetQstatLpRedDropPkts',
    'jnxCosIfsetQstatMLpRedDropPkts',
    'jnxCosIfsetQstatMHpRedDropPkts',
    'jnxCosIfsetQstatHpRedDropPkts',
    'jnxCosIfsetQstatLpRedDropBytes',
    'jnxCosIfsetQstatMLpRedDropBytes',
    'jnxCosIfsetQstatMHpRedDropBytes',
    'jnxCosIfsetQstatHpRedDropBytes',
    'jnxCosIfsetQstatRateLimitDropPkts',
    'jnxCosIfsetQstatRateLimitDropBytes',
]

COS_RATES = [
    'jnxCosIfsetQstatQedPktRate',
    'jnxCosIfsetQstatQedByteRate',
    'jnxCosIfsetQstatTxedPktRate',
    'jnxCosIfsetQstatTxedByteRate',
    'jnxCosIfsetQstatTailDropPktRate',
    'jnxCosIfsetQstatTotalRedDropPktRate',
    'jnxCosIfsetQstatLpNonTcpRDropPktRate',
    'jnxCosIfsetQstatLpTcpRedDropPktRate',
    'jnxCosIfsetQstatHpNonTcpRDropPktRate',
    'jnxCosIfsetQstatHpTcpRedDropPktRate',
    'jnxCosIfsetQstatTotalRedDropByteRate',
    'jnxCosIfsetQstatLpNonTcpRDropByteRate',
    'jnxCosIfsetQstatLpTcpRedDropByteRate',
    'jnxCosIfsetQstatHpNonTcpRDropByteRate',
    'jnxCosIfsetQstatHpTcpRedDropByteRate',
    'jnxCosIfsetQstatLpRedDropPktRate',
    'jnxCosIfsetQstatMLpRedDropPktRate',
    'jnxCosIfsetQstatMHpRedDropPktRate',
    'jnxCosIfsetQstatHpRedDropPktRate',
    'jnxCosIfsetQstatLpRedDropByteRate',
    'jnxCosIfsetQstatMLpRedDropByteRate',
    'jnxCosIfsetQstatMHpRedDropByteRate',
    'jnxCosIfsetQstatHpRedDropByteRate',
    'jnxCosIfsetQstatRateLimitDropPktRate',
    'jnxCosIfsetQstatRateLimitDropByteRate',
]

FIREWALL_COUNTS = [
    'jnxFWCounterPacketCount',
    'jnxFWCounterByteCount',
]

USER_FIREWALL = ['jnxUserFwLDAPTotalQuery', 'jnxUserFwLDAPFailedQuery']

DCU_COUNTS = ['jnxDcuStatsPackets', 'jnxDcuStatsBytes']

SCU_COUNTS = ['jnxScuStatsPackets', 'jnxScuStatsBytes']

APC_UPS_METRICS = [
    'upsAdvBatteryNumOfBattPacks',
    'upsAdvBatteryNumOfBadBattPacks',
    'upsAdvBatteryReplaceIndicator',
    'upsAdvBatteryRunTimeRemaining',
    'upsAdvBatteryTemperature',
    'upsAdvBatteryCapacity',
    'upsHighPrecInputFrequency',
    'upsHighPrecInputLineVoltage',
    'upsHighPrecOutputCurrent',
    'upsAdvInputLineFailCause',
    'upsAdvOutputLoad',
    'upsBasicBatteryTimeOnBattery',
    'upsAdvTestDiagnosticsResults',
    'upsHighPrecExtdBatteryTemperature',
    'upsAdvInputLineVoltage',
    'upsAdvInputFrequency',
    'upsAdvOutputVoltage',
    'upsAdvOutputFrequency',
    'upsAdvOutputCurrent',
    'upsAdvOutputActivePower',
    'upsAdvOutputApparentPower',
    'upsAdvOutputEnergyUsage',
    'uioSensorStatusTemperatureDegC',
]

APC_UPS_UPS_BASIC_STATE_OUTPUT_STATE_METRICS = [
    # metric, value
    ('snmp.upsBasicStateOutputState.AVRTrimActive', 1),
    ('snmp.upsBasicStateOutputState.BatteriesDischarged', 1),
    ('snmp.upsBasicStateOutputState.LowBatteryOnBattery', 1),
    ('snmp.upsBasicStateOutputState.NoBatteriesAttached', 1),
    ('snmp.upsBasicStateOutputState.On', 1),
    ('snmp.upsBasicStateOutputState.OnLine', 0),
    ('snmp.upsBasicStateOutputState.ReplaceBattery', 1),
]
