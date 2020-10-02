#!/bin/bash

echo '=> detecting IP'
export IP=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
export IOT_EDGE_DEVICE_HOSTNAME="host.docker.internal"
ping -q -c1 $IOT_EDGE_DEVICE_HOSTNAME > /dev/null 2>&1
if [ $? -ne 0 ]; then
  IOT_EDGE_DEVICE_HOSTNAME=$(ip route | awk '/default/ { print $3 }' | awk '!seen[$0]++')
fi

echo '=> creating config.yaml'
cat <<EOF > /etc/iotedge/config.yaml
provisioning:
  source: "manual"
  device_connection_string: "$IOT_EDGE_DEVICE_CONNECTION_STRING"
agent:
  name: "edgeAgent"
  type: "docker"
  env: {}
  config:
    image: "$IOT_EDGE_AGENT_IMAGE"
    auth: {}
hostname: "edgehub"
connect:
  # Use an HTTP endpoint, because mounting Unix sockets is not supported on Docker for macOS.
  # See: https://github.com/docker/for-mac/issues/483
  management_uri: "http://$IOT_EDGE_DEVICE_HOSTNAME:15580"
  workload_uri: "http://$IOT_EDGE_DEVICE_HOSTNAME:15581"
listen:
  management_uri: "http://$IP:15580"
  workload_uri: "http://$IP:15581"
homedir: "/var/lib/iotedge"
moby_runtime:
  docker_uri: "/var/run/docker.sock"
  network: "$IOT_EDGE_NETWORK"
EOF

if [ $IOT_EDGE_TLS_ENABLED ]; then
  cat <<EOF >> /etc/iotedge/config.yaml
certificates:
  device_ca_cert: $IOT_EDGE_DEVICE_CA_CERT
  device_ca_pk: $IOT_EDGE_DEVICE_CA_PK
  trusted_ca_certs: $IOT_EDGE_TRUSTED_CA_CERTS
EOF
fi

cat /etc/iotedge/config.yaml

echo '=> running iotedge daemon'
exec iotedged -c /etc/iotedge/config.yaml
