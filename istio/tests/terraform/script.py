#!/usr/bin/python

# Write it as a python script for portability
import glob
import os
from subprocess import check_call

version = os.environ['ISTIO_VERSION']
opj = os.path.join

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
check_call(["kubectl", "label", "namespace", "default", "istio-injection=enabled"])

istio = "istio-{}".format(version)

for f in glob.glob(opj(istio, "install", "kubernetes", "helm", "istio-init", "files", "crd*.yaml")):
    check_call(["kubectl", "apply", "-f", f])

check_call(["kubectl", "apply", "-f", opj(istio, "install", "kubernetes", "istio-demo-auth.yaml")])
check_call(
    ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "istio-system", "--timeout=300s"]
)

check_call(["kubectl", "apply", "-f", opj(istio, "samples", "bookinfo", "platform", "kube", "bookinfo.yaml")])
check_call(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])

check_call(["kubectl", "apply", "-f", opj(istio, "samples", "bookinfo", "networking", "bookinfo-gateway.yaml")])
check_call(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])
