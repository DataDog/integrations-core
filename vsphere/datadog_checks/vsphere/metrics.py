from pyVmomi import vim

#https://www.vmware.com/support/developer/converter-sdk/conv61_apireference/vim.PerformanceManager.MetricId.html
#instance values : None is aggregate , * is all instances
#also supports comma separated specific instance values

# All metrics that can be collected from VirtualMachines.
VM_METRICS = {
    'cpu.ready.summation' : None,
    'cpu.usage.average' : None,
    'mem.usage.average' : None,
    'mem.active.average' : None,
    'mem.vmmemctl.average' : None,
    'mem.consumed.average' : None,
    'mem.shared.average' : None,
    'mem.swapped.average' : None,
    'datastore.numberReadAveraged.average' : "*",
    'datastore.numberWriteAveraged.average' : "*",
    'datastore.read.average' : "*",
    'datastore.write.average' : "*",
    'datastore.totalReadLatency.average' : "*",
    'datastore.totalWriteLatency.average' : "*",
    'datastore.maxTotalLatency.latest' : None,
    'disk.usage.average' : None,
    'disk.numberReadAveraged.average' : "*",
    'disk.numberWriteAveraged.average' : "*",
    'disk.read.average' : "*",
    'disk.write.average' : "*",
    'disk.maxTotalLatency.latest' : None,
    'virtualDisk.numberReadAveraged.average' : "*",
    'virtualDisk.numberWriteAveraged.average' : "*",
    'virtualDisk.read.average' : None,
    'virtualDisk.write.average' : None,
    'virtualDisk.totalReadLatency.average' : "*",
    'virtualDisk.totalWriteLatency.average' : "*",
    'net.usage.average' : None,
    'net.bytesRx.average' : None,
    'net.bytesTx.average' : None,
    'net.droppedRx.summation' : None,
    'net.droppedTx.summation' : None,
}

# All metrics that can be collected from ESXi Hosts.
HOST_METRICS = {
    'cpu.ready.summation' : None,
    'cpu.usage.average' : None,
    'mem.usage.average' : None,
    'datastore.numberReadAveraged.average' : "*",
    'datastore.numberWriteAveraged.average' : "*",
    'datastore.read.average' : "*",
    'datastore.write.average' : "*",
    'datastore.datastoreIops.average' : "*",
    'datastore.datastoreReadIops.latest' : "*",
    'datastore.datastoreWriteIops.latest' : "*",
    'datastore.totalReadLatency.average' : "*",
    'datastore.totalWriteLatency.average' : "*",
    'datastore.maxTotalLatency.latest' : None,
    'disk.usage.average' : None,
    'disk.numberReadAveraged.average' : "*",
    'disk.numberWriteAveraged.average' : "*",
    'disk.read.average' : "*",
    'disk.write.average' : "*",
    'disk.maxTotalLatency.latest' : None,
    'disk.totalReadLatency.average' : "*",
    'disk.totalWriteLatency.average' : "*",
}

# All metrics that can be collected from Datastores.
DATASTORE_METRICS = {
    'datastore.numberReadAveraged.average' : "*",
    'datastore.numberWriteAveraged.average' : "*",
    'disk.capacity.latest' : None,
    'disk.provisioned.latest' : None,
    'disk.used.latest' : None,
    'disk.numberReadAveraged.average' : "*",
    'disk.numberWriteAveraged.average' : "*",
}

# All metrics that can be collected from Clusters.
CLUSTER_METRICS = {
    'cpu.usage.average' : None,
    'cpu.usagemhz.average' : None,
    'mem.usage.average' : None,
    'vmop.numClone.latest' : None,
    'vmop.numCreate.latest' : None,
    'vmop.numDestroy.latest' : None,
    'vmop.numPoweroff.latest' : None,
    'vmop.numPoweron.latest' : None,
    'vmop.numRebootGuest.latest' : None,
    'vmop.numRegister.latest' : None,
    'vmop.numReset.latest' : None,
    'vmop.numSVMotion.latest' : None,
    'vmop.numShutdownGuest.latest' : None,
    'vmop.numStandbyGuest.latest' : None,
    'vmop.numSuspend.latest' : None,
    'vmop.numUnregister.latest' : None,
    'vmop.numVMotion.latest' : None,
    }

ALLOWED_METRICS_FOR_MOR = {
    vim.VirtualMachine: VM_METRICS,
    vim.HostSystem: HOST_METRICS,
    vim.Datastore: DATASTORE_METRICS,
    vim.ClusterComputeResource: CLUSTER_METRICS,
}
