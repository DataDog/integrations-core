# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

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
UDP_COUNTS = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']
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
IF_GAUGES = ['ifAdminStatus', 'ifOperStatus']

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

FRU_METRICS = [
    "cefcFRUPowerAdminStatus",
    "cefcFRUPowerOperStatus",
    "cefcFRUCurrent",
]

CPU_METRICS = [
    "cpmCPUTotalMonIntervalValue",
    "cpmCPUMemoryUsed",
    "cpmCPUMemoryFree",
]

CIE_METRICS = [
    "cieIfLastInTime",
    "cieIfLastOutTime",
    "cieIfInputQueueDrops",
    "cieIfOutputQueueDrops",
]
