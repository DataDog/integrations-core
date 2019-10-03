# Memory stats
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysStatMemoryTotal
  forced_type: gauge
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysStatMemoryUsed
  forced_type: gauge
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysGlobalTmmStatMemoryTotal
  forced_type: gauge
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysGlobalTmmStatMemoryUsed
  forced_type: gauge
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysGlobalHostOtherMemoryTotal
  forced_type: gauge
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysGlobalHostOtherMemoryUsed
  forced_type: gauge
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysGlobalHostSwapTotal
  forced_type: gauge
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysGlobalHostSwapUsed
  forced_type: gauge
# CPU stats
- MIB: F5-BIGIP-SYSTEM-MIB
  table: sysMultiHostCpuTable
  symbols:
    - sysMultiHostCpuUser
    - sysMultiHostCpuNice
    - sysMultiHostCpuSystem
    - sysMultiHostCpuIdle
    - sysMultiHostCpuIrq
    - sysMultiHostCpuSoftirq
    - sysMultiHostCpuIowait
  metric_tags:
    - tag: cpu
      column: sysMultiHostCpuId
# Basic interface stats
- MIB: IF-MIB
  table: ifTable
  symbols:
    - ifInOctets
    - ifInErrors
    - ifOutOctets
    - ifOutErrors
  metric_tags:
    - tag: interface
      column: ifDescr
# TCP stats
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysTcpStatOpen
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysTcpStatCloseWait
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysTcpStatFinWait
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysTcpStatTimeWait
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysTcpStatAccepts
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysTcpStatAcceptfails
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysTcpStatConnects
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysTcpStatConnfails
# UDP stats
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysUdpStatOpen
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysUdpStatAccepts
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysUdpStatAcceptfails
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysUdpStatConnects
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysUdpStatConnfails
# SSL stats
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysClientsslStatCurConns
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysClientsslStatEncryptedBytesIn
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysClientsslStatEncryptedBytesOut
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysClientsslStatDecryptedBytesIn
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysClientsslStatDecryptedBytesOut
- MIB: F5-BIGIP-SYSTEM-MIB
  symbol: sysClientsslStatHandshakeFailures
