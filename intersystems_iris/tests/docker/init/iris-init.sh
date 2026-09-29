#!/bin/bash
# Post-start hook (wired via `iris-main --after`) that makes the interoperability
# metric families (iris_interop_*) appear on /api/monitor/metrics.
#
# The families are runtime-gated: they only materialize once an interop-enabled
# namespace has a RUNNING production. A vanilla IRIS container emits system
# metrics only. This script therefore, on every boot:
#   1. ensures the USER namespace is interoperability-enabled (idempotent),
#   2. loads + starts a minimal demo production,
#   3. pushes a small burst of test messages so the counters are non-zero.
set -euo pipefail

# `iris session` exits 0 no matter what the ObjectScript did, and `halt` cannot set an exit code,
# so each block below reports its own outcome: a `FATAL:` line for a bad %Status, and a terminating
# `DONE:` line whose absence also catches unhandled runtime errors (<UNDEFINED>, a compile error)
# that abort the block before any FATAL is written. Without this the first failure stays silent
# until the readiness gate in conftest.py times out with a generic "metrics never appeared".
run_objectscript() {
    local label=$1 namespace=$2 output
    output=$(iris session IRIS -U "$namespace")
    echo "$output"

    if grep -q '^FATAL:' <<<"$output"; then
        echo "[iris-init] $label failed: $(grep '^FATAL:' <<<"$output")" >&2
        exit 1
    fi
    if ! grep -q '^DONE:' <<<"$output"; then
        echo "[iris-init] $label did not run to completion (no DONE marker); see output above" >&2
        exit 1
    fi
}

echo "[iris-init] enabling interoperability on USER namespace"
run_objectscript "enable interoperability" %SYS <<'OSCRIPT'
set sc=##class(%Library.EnsembleMgr).EnableNamespace("USER")
if '$system.Status.IsOK(sc) { write "FATAL: EnableNamespace: ",$system.Status.GetOneStatusText(sc),! halt }
write "DONE: EnableNamespace",!
halt
OSCRIPT

echo "[iris-init] loading + starting Demo.MonitorProduction and generating traffic"
# NOTE: Ens.Util.Statistics is an ENSLIB class mapped only into interop-enabled
# namespaces, so this whole block must run from USER (not %SYS). SAM interop
# sampling is a persisted per-namespace flag and is the step that actually makes
# the iris_interop_* families appear on /api/monitor/metrics.
run_objectscript "start production" USER <<'OSCRIPT'
set sc=##class(Ens.Util.Statistics).EnableSAMForNamespace()
if '$system.Status.IsOK(sc) { write "FATAL: EnableSAMForNamespace: ",$system.Status.GetOneStatusText(sc),! halt }
set sc=$system.OBJ.Load("/opt/irisinit/MonitorProduction.cls","ck")
if '$system.Status.IsOK(sc) { write "FATAL: Load MonitorProduction.cls: ",$system.Status.GetOneStatusText(sc),! halt }
set sc=##class(Ens.Director).StartProduction("Demo.MonitorProduction")
if '$system.Status.IsOK(sc) { write "FATAL: StartProduction: ",$system.Status.GetOneStatusText(sc),! halt }
hang 5
set sc=##class(Ens.Director).CreateBusinessService("EnsLib.Testing.Service",.svc)
if '$system.Status.IsOK(sc) { write "FATAL: CreateBusinessService: ",$system.Status.GetOneStatusText(sc),! halt }
set ok=0 for i=1:1:200 { set req=##class(Ens.StringRequest).%New(),req.StringValue="init-load-"_i set s=svc.SendRequestAsync("TestProcess",req) if $system.Status.IsOK(s) { set ok=ok+1 } }
if ok=0 { write "FATAL: no test messages were accepted by TestProcess",! halt }
write "DONE: messages sent: ",ok,!
halt
OSCRIPT

echo "[iris-init] done"
