#!/usr/bin/python

# Write it as a python script for portability
import glob
import os
from subprocess import check_call

version = os.environ['CILIUM_VERSION']
opj = os.path.join
# TODO: Create cluster-admin-binding
# kubectl create clusterrolebinding cluster-admin-binding --clusterrole cluster-admin --user your@google.email

# We don't care about the platform as we only use yaml files
check_call(
    [
        "curl",
        "-o",
        "cilium.tar.gz",  # Need to update with versions where possible
        "-L",
        "https://github.com/cilium/cilium/archive/master.tar.gz".format(
            version=version
        ),
    ]
)
check_call(["tar", "xf", "cilium.tar.gz"])

check_call(["cd", "cilium-master/install/kubernetes"])

check_call(["kubectl", "create", "ns", "cilium-system"])

cilium = "cilium-{}".format(version)

# TODO: update with the following helm
"""
helm template cilium \
  --namespace cilium \
  --set global.nodeinit.enabled=true \
  --set nodeinit.reconfigureKubelet=true \
  --set nodeinit.removeCbrBridge=true \
  --set global.cni.binPath=/home/kubernetes/bin \
  > cilium.yaml
"""
for f in glob.glob(opj(cilium, "install", "kubernetes", "helm", "cilium-init", "files", "crd*.yaml")):
    check_call(["kubectl", "apply", "-f", f])

