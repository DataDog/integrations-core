# Tests

This check ships unit tests only (`test_unit.py`), covering pure parser
functions against the fixtures in `fixtures/` and full `check()` runs with
`get_subprocess_output` mocked via an argv-dispatch table.

There is intentionally no `test_integration.py`, `test_e2e.py`, or
`dd_environment`: there is no AIX CI runner available, and PowerHA cannot be
meaningfully containerized — it requires the CAA kernel extension and real
(or SAN-backed) shared storage across multiple AIX nodes. A `dd_environment`
here would not be able to run PowerHA itself, so it would add maintenance
cost without exercising real behavior.

The acceptance test for changes to this check is manual: install it on a
real PowerHA 7.2+ node, run `agent check powerha`, and compare its emitted
metrics/service checks against `qha -nvemc` run at the same moment on the
same node. See `fixtures/README.md` for fixture provenance and known
version-sensitivity risks.
