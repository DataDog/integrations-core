# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

MINUTE_STATS_INTERVAL = 60

# tunnel_availability_v2.txt column indices (0-based, no header)
TUNNEL_AVAIL_COL_ALIAS = 2
TUNNEL_AVAIL_COL_SECONDS_DOWN = 8
TUNNEL_AVAIL_COL_COLOR = 13

# probe_v2.txt column indices (0-based, no header)
PROBE_COL_PROBE_NAME = 2
PROBE_COL_AVG_LATENCY = 8
PROBE_COL_AVG_LOSS = 10
PROBE_COL_AVG_JITTER = 12
PROBE_COL_ADMIN_UP = 13
PROBE_COL_OPER_UP = 14

# appperf_v2.txt column indices (0-based, no header)
APPPERF_COL_APP_NAME = 2
APPPERF_COL_TUNNEL_NAME = 3
APPPERF_COL_TRANSPORT_TYPE = 4
APPPERF_COL_CND_DELAY = 5
APPPERF_COL_SND_DELAY = 6
APPPERF_COL_APP_DELAY = 8

# tunnel_v2.txt column indices (0-based, no header)
TUNNEL_V2_COL_TUNNEL_ID = 1
TUNNEL_V2_COL_ALIAS = 2
TUNNEL_V2_COL_OVERLAY_ID = 3
TUNNEL_V2_COL_IS_SDWAN = 4
TUNNEL_V2_COL_BYTES_WAN_TX = 6
TUNNEL_V2_COL_BYTES_WAN_RX = 7
TUNNEL_V2_COL_BYTES_LAN_TX = 8
TUNNEL_V2_COL_BYTES_LAN_RX = 9
TUNNEL_V2_COL_PKTS_WAN_TX = 10
TUNNEL_V2_COL_PKTS_WAN_RX = 11
TUNNEL_V2_COL_PKTS_LAN_TX = 12
TUNNEL_V2_COL_PKTS_LAN_RX = 13
TUNNEL_V2_COL_LATENCY_AVG = 14
TUNNEL_V2_COL_LATENCY_MIN = 15
TUNNEL_V2_COL_LOSS_PCT_PREFEC = 23
TUNNEL_V2_COL_LOSS_PCT_POSTFEC = 24

# Tunnel type value for internet breakout
TUNNEL_TYPE_INTERNET_BREAKOUT = (
    2  # https://github.com/aruba/pyedgeconnect/blob/main/pyedgeconnect/orch/_timeseries_stats.py#L1913
)

# NDM resource tag prefixes (used by the backend to correlate metrics with NDM entities)
NDM_DEVICE_RESOURCE_TAG = 'dd.internal.resource:ndm_device'
NDM_DEVICE_USER_TAGS_RESOURCE_TAG = 'dd.internal.resource:ndm_device_user_tags'
NDM_INTERFACE_RESOURCE_TAG = 'dd.internal.resource:ndm_interface'
