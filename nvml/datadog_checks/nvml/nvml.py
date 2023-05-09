# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import os.path
import threading
import time

import grpc
import pynvml

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.tagging import tagger

from .api_pb2 import ListPodResourcesRequest
from .api_pb2_grpc import PodResourcesListerStub

METRIC_PREFIX = "nvml."
SOCKET_PATH = "/var/lib/kubelet/pod-resources/kubelet.sock"
"""Assumed to be a UDS accessible from this running code"""


class NvmlInit(object):
    """Wraps an nvmlInit and an nvmlShutdown inside the same context"""

    def __enter__(self):
        NvmlCheck.N.nvmlInit()

    def __exit__(self, exception_type, exception_value, traceback):
        NvmlCheck.N.nvmlShutdown()


class NvmlCall(object):
    previously_printed_errors = set()
    """Wraps a call and checks for an exception (of any type).

       Why this exists: If a graphics card doesn't support a nvml method, we don't want to spam the logs with just
       that method's errors, but we don't want to never error.  And we don't want to fail all the
       metrics, just the metrics that aren't supported.  This class supports that use case.

       NvmlCall wraps a call and checks for an exception (of any type).  If an exception is raised
       then that error is logged, but only logged once for this type of call
    """

    def __init__(self, name, logger):
        self.name = name
        self.log = logger

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        # Do nothing if the exception is not from pynvml or there is no exception
        if traceback is None:
            return False
        if not issubclass(exception_type, pynvml.NVMLError):
            return False

        # Suppress pynvml exceptions so we can continue
        if self.name in NvmlCall.previously_printed_errors:
            return True
        NvmlCall.previously_printed_errors.add(self.name)
        self.log.warning("Unable to execute NVML function: %s: %s", self.name, exception_value)
        return True


class NvmlCheck(AgentCheck):
    __NAMESPACE__ = "nvml"
    N = pynvml
    """The pynvml package, explicitly assigned, used for easy test mocking."""
    known_tags = {}
    """A map of GPU UUIDs to the k8s tags we should assign that GPU."""
    lock = threading.Lock()
    """Lock for the object known_tags."""
    _thread = None
    """Daemon thread updating k8s tag information in the background."""
    should_run = False
    """Whether libnvml can be found and the check can thus run."""

    def __init__(self, name, init_config, instances):
        super(NvmlCheck, self).__init__(name, init_config, instances)
        # self.N = pynvml
        if self.is_nvml_library_available():
            # Start thread once and keep it running in the background
            self._start_discovery()
            self.should_run = True

    def is_nvml_library_available(self):
        try:
            self.N.nvmlInit()
            self.N.nvmlShutdown()
            return True
        except pynvml.nvml.NVMLError_LibraryNotFound:
            self.log.warning("Can't open NVML, is this a GPU host? Turning check off.")
            return False

    def check(self, instance):
        if not self.should_run:
            # No kubelet socket or no NVML library, skip the check
            return
        with NvmlInit():
            self.gather(instance)

    def gather(self, instance):
        with NvmlCall("device_count", self.log):
            deviceCount = NvmlCheck.N.nvmlDeviceGetCount()
            self.gauge('device_count', deviceCount)
            for i in range(deviceCount):
                handle = NvmlCheck.N.nvmlDeviceGetHandleByIndex(i)
                uuid = NvmlCheck.N.nvmlDeviceGetUUID(handle)
                # The tags used by https://github.com/NVIDIA/gpu-monitoring-tools/blob/master/exporters/prometheus-dcgm/dcgm-exporter/dcgm-exporter # noqa: E501
                tags = ["gpu:" + str(i)]
                # Appends k8s specific tags
                tags += self.get_tags(uuid)
                self.gather_gpu(handle, tags)

    def gather_gpu(self, handle, tags):
        """Gather metrics for a specific GPU"""
        # Utilization information for a device. Each sample period may be
        # between 1 second and 1/6 second, depending on the product being
        # queried.  Taking names to match
        # https://github.com/NVIDIA/gpu-monitoring-tools/blob/master/exporters/prometheus-dcgm/dcgm-exporter/dcgm-exporter # noqa: E501
        # Documented at https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html # noqa: E501
        with NvmlCall("util_rate", self.log):
            util = NvmlCheck.N.nvmlDeviceGetUtilizationRates(handle)
            self.gauge('gpu_utilization', util.gpu, tags=tags)
            self.gauge('mem_copy_utilization', util.memory, tags=tags)

        # See https://docs.nvidia.com/deploy/nvml-api/structnvmlMemory__t.html#structnvmlMemory__t
        with NvmlCall("mem_info", self.log):
            mem_info = NvmlCheck.N.nvmlDeviceGetMemoryInfo(handle)
            self.gauge('fb_free', mem_info.free, tags=tags)
            self.gauge('fb_used', mem_info.used, tags=tags)
            self.gauge('fb_total', mem_info.total, tags=tags)

        # See https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html#group__nvmlDeviceQueries_1g7ef7dff0ff14238d08a19ad7fb23fc87 # noqa: E501
        with NvmlCall("power", self.log):
            power = NvmlCheck.N.nvmlDeviceGetPowerUsage(handle)
            self.gauge('power_usage', power, tags=tags)

        # https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html#group__nvmlDeviceQueries_1g732ab899b5bd18ac4bfb93c02de4900a
        with NvmlCall("total_energy_consumption", self.log):
            consumption = NvmlCheck.N.nvmlDeviceGetTotalEnergyConsumption(handle)
            self.monotonic_count('total_energy_consumption', consumption, tags=tags)

        # https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html#group__nvmlDeviceQueries_1ga5c77a2154a20d4e660221d8592d21fb
        with NvmlCall("enc_utilization", self.log):
            encoder_util = NvmlCheck.N.nvmlDeviceGetEncoderUtilization(handle)
            self.gauge('enc_utilization', encoder_util[0], tags=tags)

        # https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html#group__nvmlDeviceQueries_1g0e3420045bc9d04dc37690f4701ced8a
        with NvmlCall("dec_utilization", self.log):
            dec_util = NvmlCheck.N.nvmlDeviceGetDecoderUtilization(handle)
            self.gauge('dec_utilization', dec_util[0], tags=tags)

        # https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html#group__nvmlDeviceQueries_1gd86f1c74f81b5ddfaa6cb81b51030c72
        with NvmlCall("pci_through", self.log):
            tx_bytes = NvmlCheck.N.nvmlDeviceGetPcieThroughput(handle, pynvml.NVML_PCIE_UTIL_TX_BYTES)
            rx_bytes = NvmlCheck.N.nvmlDeviceGetPcieThroughput(handle, pynvml.NVML_PCIE_UTIL_RX_BYTES)
            self.monotonic_count('pcie_tx_throughput', tx_bytes, tags=tags)
            self.monotonic_count('pcie_rx_throughput', rx_bytes, tags=tags)

        # https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html#group__nvmlDeviceQueries_1g92d1c5182a14dd4be7090e3c1480b121
        with NvmlCall("temperature", self.log):
            temp = NvmlCheck.N.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            self.gauge('temperature', temp, tags=tags)

        # https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html#group__nvmlDeviceQueries_1ge8e3e5b5b9dcf436e4537982cf647d4e
        with NvmlCall("fan_speed", self.log):
            fan_speed = NvmlCheck.N.nvmlDeviceGetFanSpeed(handle)
            self.gauge('fan_speed', fan_speed, tags=tags)

        with NvmlCall("compute_running_processes", self.log):
            compute_running_processes = NvmlCheck.N.nvmlDeviceGetComputeRunningProcesses_v2(handle)
            for compute_running_process in compute_running_processes:
                self.gauge(
                    'compute_running_process',
                    compute_running_process.usedGpuMemory,
                    tags=tags + [f"pid:{compute_running_process.pid}"],
                )

    def _start_discovery(self):
        """Start daemon thread to discover which k8s pod is assigned to a GPU"""
        # type: () -> None
        if not os.path.exists(SOCKET_PATH):
            self.log.info("No kubelet socket at %s.  Not monitoring k8s pod tags", SOCKET_PATH)
            return
        self.log.info("Monitoring kubelet tags at %s", SOCKET_PATH)
        self._thread = threading.Thread(target=self.discover_instances, args=(10,), name=self.name, daemon=True)
        self._thread.daemon = True
        self._thread.start()

    def discover_instances(self, interval):
        try:
            while True:
                self.refresh_tags()
                time.sleep(interval)
        except Exception as ex:
            self.log.error(ex)
        finally:
            self.log.warning("discover_instances finished.  No longer refreshing instance tags")

    def get_tags(self, device_id):
        with self.lock:
            # Note: device ID comes in as bytes, but we get strings from grpc
            return self.known_tags.get(device_id, self.known_tags.get(device_id, []))

    def get_pod_tags(self, namespace, pod_name):
        try:
            uid_length = 36
            pod_uid = None
            prefix = f"{namespace}_{pod_name}_"
            for d in os.listdir("/var/log/pods"):
                if len(d) != len(prefix) + uid_length:
                    continue
                if not d.startswith(prefix):
                    continue
                pod_uid = d[-uid_length:]
                break
            if pod_uid is None:
                return []
            return tagger.get_tags(f"kubernetes_pod_uid://{pod_uid}", tagger.LOW)
        except Exception:
            self.log.error("Could not get tags for %s pod %s", namespace, pod_name)
            return []

    def refresh_tags(self):
        channel = grpc.insecure_channel('unix://' + SOCKET_PATH)
        stub = PodResourcesListerStub(channel)
        response = stub.List(ListPodResourcesRequest())
        new_tags = {}
        for pod_res in response.pod_resources:
            for container in pod_res.containers:
                for device in container.devices:
                    if device.resource_name != "nvidia.com/gpu":
                        continue
                    pod_name = pod_res.name
                    kube_namespace = pod_res.namespace
                    kube_container_name = container.name
                    pod_tags = self.get_pod_tags(kube_namespace, pod_name)
                    for device_id in device.device_ids:
                        # These are the tag names that datadog seems to use
                        new_tags[device_id] = [
                            "pod_name:" + pod_name,
                            "kube_namespace:" + kube_namespace,
                            "kube_container_name:" + kube_container_name,
                        ] + pod_tags
        with self.lock:
            self.known_tags = new_tags
