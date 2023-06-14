FROM datadog/agent:latest
# COPY datadog_checks_base/datadog_checks/base/checks/base.py /opt/datadog-agent/embedded/lib/python3.8/site-packages/datadog_checks/base/checks/base.py
COPY kubelet/datadog_checks/kubelet/kubelet.py    /opt/datadog-agent/embedded/lib/python3.8/site-packages/datadog_checks/kubelet/kubelet.py
COPY kubelet/datadog_checks/kubelet/probes.py     /opt/datadog-agent/embedded/lib/python3.8/site-packages/datadog_checks/kubelet/probes.py
COPY kubelet/datadog_checks/kubelet/prometheus.py /opt/datadog-agent/embedded/lib/python3.8/site-packages/datadog_checks/kubelet/prometheus.py
COPY kube_apiserver_metrics/datadog_checks/kube_apiserver_metrics/kube_apiserver_metrics.py /opt/datadog-agent/embedded/lib/python3.8/site-packages/datadog_checks/kube_apiserver_metrics/kube_apiserver_metrics.py

