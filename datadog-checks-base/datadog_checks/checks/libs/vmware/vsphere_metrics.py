'''
Created on 11-Mar-2020

@author: atish.bhowmick
'''

CPU_METRICS = {
    'cpu.ready': {
        's_type'       : 'delta',
        'unit'         : 'millisecond',
        'rollup'       : 'summation',
        'entity'       : ['VirtualMachine', 'HostSystem']
    },
    'cpu.usage': {
        's_type'       : 'rate',
        'unit'         : 'percent',
        'rollup'       : 'average',
        'entity'       : ['VirtualMachine', 'HostSystem']
    },
}
MEM_METRICS = {
    'mem.usage': {
        's_type': 'absolute',
        'unit': 'percent',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Active
    'mem.active': {
        's_type': 'absolute',
        'unit': 'kiloBytes',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Balloon
    'mem.vmmemctl': {
        's_type': 'absolute',
        'unit': 'kiloBytes',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Consumed
    'mem.consumed': {
        's_type': 'absolute',
        'unit': 'kiloBytes',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Shared
    'mem.shared': {
        's_type': 'absolute',
        'unit': 'kiloBytes',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Swapped
    'mem.swapped': {
        's_type': 'absolute',
        'unit': 'kiloBytes',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
}
DATASTORE_METRICS = {
    # Average read requests per second
    'datastore.numberReadAveraged': {
        's_type': 'rate',
        'unit': 'number',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Average write requests per second
    'datastore.numberWriteAveraged': {
        's_type': 'rate',
        'unit': 'number',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Read rate
    'datastore.read': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    #Write rate
    'datastore.write': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Storage I/O Control aggregated IOPS
    'datastore.datastoreIops': {
        's_type': 'absolute',
        'unit': 'number',
        'rollup': 'average',
        'entity': ['HostSystem']
    },
    # Storage DRS datastore read I/O rate
    'datastore.datastoreReadIops': {
        's_type': 'absolute',
        'unit': 'number',
        'rollup': 'latest',
        'entity': ['HostSystem']
    },
    # Storage DRS datastore write I/O rate
    'datastore.datastoreWriteIops': {
        's_type': 'absolute',
        'unit': 'number',
        'rollup': 'latest',
        'entity': ['HostSystem']
    },
    # Read latency
    'datastore.totalReadLatency': {
        's_type': 'absolute',
        'unit': 'millisecond',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Write latency
    'datastore.totalWriteLatency': {
        's_type': 'absolute',
        'unit': 'millisecond',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Highest latency
    'datastore.maxTotalLatency': {
        's_type': 'absolute',
        'unit': 'millisecond',
        'rollup': 'latest',
        'entity': ['VirtualMachine', 'HostSystem']
    },
}
DISK_METRICS = {
    # Usage
    'disk.usage': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Average read requests per second
    'disk.numberReadAveraged': {
        's_type': 'rate',
        'unit': 'number',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Average write requests per second
    'disk.numberWriteAveraged': {
        's_type': 'rate',
        'unit': 'number',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Read rate
    'disk.read': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Write rate
    'disk.write': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Highest latency
    'disk.maxTotalLatency': {
        's_type': 'absolute',
        'unit': 'millisecond',
        'rollup': 'latest',
        'entity': ['VirtualMachine', 'HostSystem']
    },
    # Read latency
    'disk.totalReadLatency': {
        's_type': 'absolute',
        'unit': 'millisecond',
        'rollup': 'average',
        'entity': ['HostSystem']
    },
    # Write latency
    'disk.totalWriteLatency': {
        's_type': 'absolute',
        'unit': 'millisecond',
        'rollup': 'average',
        'entity': ['HostSystem']
    },
}
VIRTUALDISK_METRICS = {
    # Average read requests per second
    'virtualDisk.numberReadAveraged': {
        's_type': 'rate',
        'unit': 'number',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Average write requests per second
    'virtualDisk.numberWriteAveraged': {
        's_type': 'rate',
        'unit': 'number',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Read rate
    'virtualDisk.read': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Write rate
    'virtualDisk.write': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Read latency
    'virtualDisk.totalReadLatency': {
        's_type': 'absolute',
        'unit': 'millisecond',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Write latency
    'virtualDisk.totalWriteLatency': {
        's_type': 'absolute',
        'unit': 'millisecond',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
}
NETWORK_METRICS = {
    # Usage
    'net.usage': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Data receive rate
    'net.bytesRx': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Data transmit rate
    'net.bytesTx': {
        's_type': 'rate',
        'unit': 'kiloBytesPerSecond',
        'rollup': 'average',
        'entity': ['VirtualMachine']
    },
    # Receive packets dropped
    'net.droppedRx': {
        's_type': 'delta',
        'unit': 'number',
        'rollup': 'summation',
        'entity': ['VirtualMachine']
    },
    # Transmit packets dropped
    'net.droppedTx': {
        's_type': 'delta',
        'unit': 'number',
        'rollup': 'summation',
        'entity': ['VirtualMachine']
    },
}

VSPHERE_METRICS = {}
VSPHERE_METRICS.update(CPU_METRICS)
VSPHERE_METRICS.update(MEM_METRICS)
VSPHERE_METRICS.update(DATASTORE_METRICS)
VSPHERE_METRICS.update(DISK_METRICS)
VSPHERE_METRICS.update(VIRTUALDISK_METRICS)
VSPHERE_METRICS.update(NETWORK_METRICS)
