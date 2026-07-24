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

echo "[iris-init] enabling interoperability on USER namespace"
iris session IRIS -U %SYS <<'OSCRIPT'
set sc=##class(%Library.EnsembleMgr).EnableNamespace("USER") write "EnableNamespace: ",$system.Status.GetOneStatusText(sc),!
halt
OSCRIPT

echo "[iris-init] loading + starting Demo.MonitorProduction and generating traffic"
# NOTE: Ens.Util.Statistics is an ENSLIB class mapped only into interop-enabled
# namespaces, so this whole block must run from USER (not %SYS). SAM interop
# sampling is a persisted per-namespace flag and is the step that actually makes
# the iris_interop_* families appear on /api/monitor/metrics.
iris session IRIS -U USER <<'OSCRIPT'
set sc=##class(Ens.Util.Statistics).EnableSAMForNamespace() write "EnableSAMForNamespace: ",$system.Status.GetOneStatusText(sc),!
do $system.OBJ.Load("/opt/irisinit/MonitorProduction.cls","ck")
set sc=##class(Ens.Director).StartProduction("Demo.MonitorProduction") write "StartProduction: ",$system.Status.GetOneStatusText(sc),!
hang 5
set tSC=##class(Ens.Director).CreateBusinessService("EnsLib.Testing.Service",.svc) write "CreateBusinessService: ",$system.Status.GetOneStatusText(tSC),!
set ok=0 for i=1:1:200 { set req=##class(Ens.StringRequest).%New(),req.StringValue="init-load-"_i set s=svc.SendRequestAsync("TestProcess",req) if $system.Status.IsOK(s) { set ok=ok+1 } }
write "messages sent: ",ok,!
halt
OSCRIPT

echo "[iris-init] done"
