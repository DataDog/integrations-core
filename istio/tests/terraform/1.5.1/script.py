#!/usr/bin/python

# Write it as a python script for portability
import os
from subprocess import check_call

version = os.environ['ISTIO_VERSION']
opj = os.path.join

HERE = os.path.dirname(os.path.abspath(__file__))

# We don't care about the platform as we only use yaml files
check_call(
    [
        "curl",
        "-o",
        "istio.tar.gz",
        "-L",
        "https://github.com/istio/istio/releases/download/{version}/istio-{version}-linux.tar.gz".format(
            version=version
        ),
    ]
)
check_call(["tar", "xf", "istio.tar.gz"])

check_call(["kubectl", "create", "ns", "istio-system"])

istio = "istio-{}".format(version)

for _ in range(2):
    try:
        check_call(["kubectl", "apply", "-f", opj(HERE, "demo_profile.yaml")])
    except Exception:
        print("Retry deploying demo profile...")

check_call(
    ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "istio-system", "--timeout=300s"]
)

check_call(["kubectl", "label", "namespace", "default", "istio-injection=enabled"])

check_call(["kubectl", "apply", "-f", opj(istio, "samples", "bookinfo", "platform", "kube", "bookinfo.yaml")])
check_call(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])

check_call(["kubectl", "apply", "-f", opj(istio, "samples", "bookinfo", "networking", "bookinfo-gateway.yaml")])
check_call(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])
