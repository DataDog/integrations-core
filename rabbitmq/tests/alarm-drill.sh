#!/bin/sh
# Periodic memory + disk alarm drill, for rabbitmq.node.mem_alarm,
# rabbitmq.node.disk_alarm (management API) and
# rabbitmq.alarms.free_disk_space.watermark (OpenMetrics). All three are 0 on a
# healthy broker.
#
# Runs inside the broker container, started in the background by the broker's
# command, so rabbitmqctl reaches the local node with the node's own cookie and
# name; a sidecar would need both shared.
#
# Every PERIOD seconds it lowers the memory watermark and raises the disk free
# limit past what the node has, holds both for WINDOW seconds, then restores the
# values read at startup. While an alarm is active the broker blocks every
# publishing connection, so the publish/confirm counters stall for that window.
# WINDOW is above the 15s scrape interval (management stats lag the alarm by up
# to ~8s at both ends, so the visible window keeps its length) and below
# perf-test's 30s confirm timeout.
set -u

WINDOW=25
PERIOD=180
FIRST_DELAY=60

log() { echo "alarm-drill: $*"; }

if [ "${ALARM_DRILL:-1}" = "0" ] || [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled (ALARM_DRILL=${ALARM_DRILL:-1}, ACTIVITY_GEN=${ACTIVITY_GEN:-1})"
  exit 0
fi

ctl() { rabbitmqctl -q "$@"; }

until rabbitmq-diagnostics -q check_running >/dev/null 2>&1; do sleep 5; done

# Settings changed through rabbitmqctl are runtime-only, so a broker restart
# also restores these.
mem=$(ctl eval 'vm_memory_monitor:get_vm_memory_high_watermark().')
disk=$(ctl eval 'rabbit_disk_monitor:get_disk_free_limit().')
case "$mem" in
  "{absolute,"*) mem="absolute $(echo "$mem" | tr -dc '0-9')" ;;
esac
log "baseline: vm_memory_high_watermark=${mem} disk_free_limit=${disk}"

restore() {
  for _ in 1 2 3 4 5; do
    # shellcheck disable=SC2086 # "absolute N" must split into two arguments
    ctl set_vm_memory_high_watermark $mem >/dev/null && ctl set_disk_free_limit "$disk" >/dev/null && return 0
    sleep 2
  done
  log "restore failed; alarms may stay raised"
  return 1
}
trap restore EXIT
trap 'exit 1' INT TERM HUP

sleep "$FIRST_DELAY"
while :; do
  log "raising memory and disk alarms for ${WINDOW}s"
  ctl set_vm_memory_high_watermark 0.0001 >/dev/null || log "raising the memory alarm failed"
  ctl set_disk_free_limit 100000GB >/dev/null || log "raising the disk alarm failed"
  sleep "$WINDOW"
  restore && log "alarms cleared"
  sleep $((PERIOD - WINDOW))
done
