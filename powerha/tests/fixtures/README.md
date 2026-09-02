# Fixture provenance

All fixtures in this directory are **hand-synthesized** from IBM's documented
AIX/PowerHA command output formats (`man` pages, IBM Knowledge Center command
references, and the field layouts implied by `PowerHA.script.sh`/`qha`'s own
`awk`/`sed` parsing). None were captured from a live cluster, because no AIX
or PowerHA environment is available in this development environment or in
CI (see `tests/README.md`).

Before merging, the following fixtures should be replaced with (or checked
against) real captures from a PowerHA 7.2+ cluster, since their exact field
layout is the least standardized / most version-sensitive of the set:

- `clrginfo_m.txt` (`clRGinfo -m` — application monitor status; layout can
  vary between paragraph-mode and tabular output across PowerHA versions)
- `lscluster_m_*.txt` (`lscluster -m` — CAA topology; verbose, deeply nested
  free-text format)
- `clras_sancomm_status.txt` / `clras_dpcomm_status.txt` (`clras` is an
  internal/undocumented CAA diagnostic command; column layout is inferred)

The remaining fixtures (`odmget_*`, `lssrc_*`, `lslpp_*`, `netstat_i*`,
`lsvg_*`) are based on stable, long-documented AIX interfaces (ODM stanza
format, `lssrc -ls`, `lslpp -Lc`, BSD-style `netstat -i`, `lsvg -p`) and are
lower risk.

The parsers in `datadog_checks/powerha/parsers.py` are written to be
tolerant of unrecognized lines (logged at `debug` and skipped) specifically
because these fixtures may not be pixel-perfect.
