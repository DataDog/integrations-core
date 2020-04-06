from pyVmomi import vim


# All metrics that can be collected from VirtualMachines.
VM_METRICS = {
    'cpu.ready.summation',
    'cpu.usage.average',
    'mem.usage.average',
    'mem.active.average',
    'mem.vmmemctl.average',
    'mem.consumed.average',
    'mem.shared.average',
    'mem.swapped.average',
    'datastore.numberReadAveraged.average',
    'datastore.numberWriteAveraged.average',
    'datastore.read.average',
    'datastore.write.average',
    'datastore.totalReadLatency.average',
    'datastore.totalWriteLatency.average',
    'datastore.maxTotalLatency.latest',
    'disk.usage.average',
    'disk.numberReadAveraged.average',
    'disk.numberWriteAveraged.average',
    'disk.read.average',
    'disk.write.average',
    'disk.maxTotalLatency.latest',
    'virtualDisk.numberReadAveraged.average',
    'virtualDisk.numberWriteAveraged.average',
    'virtualDisk.read.average',
    'virtualDisk.write.average',
    'virtualDisk.totalReadLatency.average',
    'virtualDisk.totalWriteLatency.average',
    'net.usage.average',
    'net.bytesRx.average',
    'net.bytesTx.average',
    'net.droppedRx.summation',
    'net.droppedTx.summation',
}

# All metrics that can be collected from ESXi Hosts.
HOST_METRICS = {
    'cpu.ready.summation',
    'cpu.usage.average',
    'mem.usage.average',
    'datastore.numberReadAveraged.average',
    'datastore.numberWriteAveraged.average',
    'datastore.read.average',
    'datastore.write.average',
    'datastore.datastoreIops.average',
    'datastore.datastoreReadIops.latest',
    'datastore.datastoreWriteIops.latest',
    'datastore.totalReadLatency.average',
    'datastore.totalWriteLatency.average',
    'datastore.maxTotalLatency.latest',
    'disk.usage.average',
    'disk.numberReadAveraged.average',
    'disk.numberWriteAveraged.average',
    'disk.read.average',
    'disk.write.average',
    'disk.maxTotalLatency.latest',
    'disk.totalReadLatency.average',
    'disk.totalWriteLatency.average',
}

# All metrics that can be collected from Datastores.
DATASTORE_METRICS = {
    'datastore.numberReadAveraged.average',
    'datastore.numberWriteAveraged.average',
    'datastore.commandsAborted.summation',
    'disk.capacity.latest',
    'disk.provisioned.latest',
    'disk.used.latest',
    'disk.numberReadAveraged.average',
    'disk.numberWriteAveraged.average',
}

# All metrics that can be collected from Clusters.
CLUSTER_METRICS = {}

ALLOWED_METRICS_FOR_MOR = {
    vim.VirtualMachine: VM_METRICS,
    vim.HostSystem: HOST_METRICS,
    vim.Datastore: DATASTORE_METRICS,
    vim.ClusterComputeResource: CLUSTER_METRICS,
}
