
METRIC_MAP = {
    # Exposed OM Metrics to map:
    'DCGM_FI_DEV_GPU_TEMP': 'temperature',
    'DCGM_FI_DEV_DEC_UTIL': 'dec_utilization',
    'DCGM_FI_DEV_ENC_UTIL': 'enc_utilization',
    'DCGM_FI_DEV_FB_FREE': 'fb_free',
    'DCGM_FI_DEV_FB_USED': 'fb_used',
    'DCGM_FI_DEV_GPU_UTIL': 'gpu_utilization',
    'DCGM_FI_DEV_MEM_CLOCK': 'mem_clock',
    'DCGM_FI_DEV_MEM_COPY_UTIL': 'mem_copy_utilization',
    'DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL': 'nvlink_bandwidth', #removed the total for processing
    'DCGM_FI_DEV_PCIE_REPLAY_COUNTER': 'pcie_replay_counter',
    'DCGM_FI_DEV_POWER_USAGE': 'power_usage',
    'DCGM_FI_DEV_SM_CLOCK': 'sm_clock',
    'DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION': 'total_energy_consumption',
    'DCGM_FI_DEV_VGPU_LICENSE_STATUS': 'vgpu_license_status',
    'DCGM_FI_DEV_XID_ERRORS': 'xid_errors',
    #NVML Specific Missing Metrics (5)
    'DCGM_FI_DEV_COUNT': 'device_count',
    'DCGM_FI_DEV_FAN_SPEED': 'fan_speed',
    'DCGM_FI_PROF_PCIE_TX_BYTES': 'pcie_tx_throughput',
    'DCGM_FI_PROF_PCIE_RX_BYTES': 'pcie_rx_throughput',
    #Others from default-counters.csv
    'DCGM_FI_DEV_MEMORY_TEMP': 'memory_temperature',
    'DCGM_FI_DEV_UNCORRECTABLE_REMAPPED_ROWS': 'uncorrectable_remapped_rows',
    'DCGM_FI_DEV_CORRECTABLE_REMAPPED_ROWS': 'correctable_remapped_rows',
    'DCGM_FI_DEV_ROW_REMAP_FAILURE': 'row_remap_failure',
}
