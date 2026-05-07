#!/bin/bash
set -euo pipefail

docker container stop dd-agent-current 2>/dev/null || :
docker container rm dd-agent-current 2>/dev/null || :
docker run --name dd-agent-current \
  	--network host \
  	-d \
  	-e DD_LOG_LEVEL=trace \
  	-e DD_HOSTNAME=demo-current \
	-e DD_CMD_PORT=5002 \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        -v /proc/:/host/proc/:ro \
        -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
        -v /sys/kernel/debug:/sys/kernel/debug \
        --cap-add=SYS_PTRACE \
        --cap-add=PERFMON \
        --cap-add=BPF \
        --security-opt apparmor=unconfined \
        -e DD_LOG_LEVEL=trace \
        -e DD_API_KEY=$DD_API_KEY \
  datadog/agent:latest
