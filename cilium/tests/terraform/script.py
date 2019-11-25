#!/usr/bin/python

# Write it as a python script for portability
import os
from subprocess import check_call

version = os.environ['CILIUM_VERSION']

opj = os.path.join

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

check_call(["kubectl", "create", "ns", "cilium"])

check_call(["kubectl", "create", "-f", config])

check_call(["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "cilium", "--timeout=300s"])

check_call(["kubectl", "wait", "pods", "-n", "cilium", "--all", "--for=condition=Ready", "--timeout=300s"])
