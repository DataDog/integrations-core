# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
MOCK_IB_COUNTER_DATA = {
    'port_rcv_data': '1000',
    'port_xmit_data': '2000',
    'port_rcv_packets': '100',
    'port_xmit_packets': '200',
}

MOCK_RDMA_COUNTER_DATA = {
    'rx_atomic_requests': '50',
    'tx_pkts': '150',
    'rx_bytes': '3000',
}

MOCK_STATUS_DATA = {
    'state': '4: ACTIVE',
    'phys_state': '5: LinkUp',
}

MOCK_RATE_DATA = '100 Gb/sec (4X EDR)'
MOCK_DEVICE_METADATA = {
    'fw_ver': '16.35.4030',
    'hca_type': 'MT4129',
    'board_id': 'MT_0000000438',
    'node_type': '1: CA',
}
MOCK_GID_ATTRS = {
    '0': {
        'netdev': 'ens5f0',
        'type': 'RoCE v2',
    },
}

MOCK_DEVICE = 'mlx5_0'
MOCK_PORT = '1'
