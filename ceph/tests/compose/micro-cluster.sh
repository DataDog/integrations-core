#!/bin/bash
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Starts a single-node Ceph cluster (three monitors, one manager, one in-memory OSD) inside the official
# `quay.io/ceph/ceph` image, which ships the daemons but does not bootstrap a cluster.
# The monitors share the container's IP, so each one listens on its own pair of ports.
set -euxo pipefail

DIR=/var/lib/ceph/micro
MONS=(a b c)
mkdir -p "${DIR}"/{osd,run,log}
HOST_IP=$(getent ahostsv4 "${HOSTNAME}" | awk '/STREAM/ {print $1; exit}')
FSID=$(uuidgen)

MON_HOST=""
MONMAP_ARGS=()
for i in "${!MONS[@]}"; do
    addr="[v2:${HOST_IP}:$((3300 + i)),v1:${HOST_IP}:$((6789 + i))]"
    MON_HOST="${MON_HOST:+${MON_HOST},}${addr}"
    MONMAP_ARGS+=(--addv "${MONS[$i]}" "${addr}")
done

cat > /etc/ceph/ceph.conf <<EOF
[global]
fsid = ${FSID}
mon host = ${MON_HOST}
mon data = ${DIR}/mon-\$id
run dir = ${DIR}/run
log file = ${DIR}/log/\$name.log
auth cluster required = none
auth service required = none
auth client required = none
auth allow insecure global id reclaim = false
osd pool default size = 1
osd crush chooseleaf type = 0
osd pool default pg autoscale mode = off
mon allow pool size one = true
mon warn on pool no redundancy = false
mon data avail warn = 5

[osd.0]
osd data = ${DIR}/osd
osd objectstore = memstore
EOF

monmaptool --create --fsid "${FSID}" "${MONMAP_ARGS[@]}" "${DIR}/monmap"
for mon in "${MONS[@]}"; do
    mkdir -p "${DIR}/mon-${mon}"
    ceph-mon --id "${mon}" --mkfs --monmap "${DIR}/monmap" --keyring /dev/null
    ceph-mon --id "${mon}"
done
ceph-mgr --id x

OSD_ID=$(ceph osd create)
ceph osd crush add "osd.${OSD_ID}" 1 root=default
ceph-osd --id "${OSD_ID}" --mkfs
ceph-osd --id "${OSD_ID}"

ceph osd pool create demo 8
ceph osd pool application enable demo rbd

exec ceph -w
