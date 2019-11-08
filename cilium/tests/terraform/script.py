#!/usr/bin/python

# Write it as a python script for portability
import os
from subprocess import check_call

# version = os.environ['CILIUM_VERSION']
version = "1.6.1"
opj = os.path.join

cilium = "cilium-{}".format(version)

HERE = os.path.dirname(os.path.abspath(__file__))
config = os.path.join(HERE, 'cilium.yaml')


check_call(
    [
        "kubectl",
        "create",
        "clusterrolebinding",
        "cluster-admin-binding",
        "--clusterrole",
        "cluster-admin",
        "--user",
        "ddtest@google.email",
    ]
)


# We don't care about the platform as we only use yaml files
check_call(
    [
        "curl",
        "-o",
        "cilium.tar.gz",  # Need to update with versions where possible
        "-L",
        "https://github.com/cilium/cilium/archive/{version}.tar.gz".format(version=version),
    ]
)
check_call(["tar", "xf", "{version}.tar.gz".format(version=version)])


check_call(["kubectl", "create", "ns", "cilium"])

check_call(["kubectl", "create", "-f", config])

# Restart pods
check_call(["kubectl", "delete", "pods", "-n", "cilium"])
