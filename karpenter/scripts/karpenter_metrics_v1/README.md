# karpenter_metrics_v1

Maintainer tool.
It prints every metric that the pinned Karpenter release registers, as a Prometheus exposition with the help text and the type of each metric.
The tests in `tests/test_metric_coverage.py` run the check on that exposition and compare the result with `metadata.csv`.

It is not part of the integration.
The wheel only contains `datadog_checks/karpenter`, and the sdist only contains `datadog_checks`, `tests` and `manifest.json` (see `pyproject.toml`).
Nothing under `scripts/` is packaged or shipped with the Agent.
CI does not run the tool, it only reads the committed fixture.

## Run it

```shell
cd karpenter/scripts/karpenter_metrics_v1
go run . > ../../tests/fixtures/karpenter_metrics_v1.txt
```

The tool takes no arguments and prints the fixture to stdout.
A one-line summary goes to stderr.
The shell empties the file before the tool runs, so restore it with `git checkout` if the tool fails.

It needs Go and network access to the Go module proxy.
Module mode must be on (`GO111MODULE=on`, some shells set it to `off`).

## Support a newer Karpenter release

1. Bump the release in `go.mod` (`go get github.com/aws/karpenter-provider-aws@<tag>`, then `go mod tidy`).
   The provider pins the matching `sigs.k8s.io/karpenter`.
2. Run the tool as above to regenerate the fixture.
3. Map the metrics the tests report as missing in `datadog_checks/karpenter/metrics.py`, and describe them in `metadata.csv`.

## How it works

The tool imports the real Karpenter packages, which register their metrics.
It builds Karpenter's controllers offline (a fake client and cloud provider, every feature gate on), so the metrics created at runtime register too.
A metric with labels has no series until something uses it, and the registry only returns metrics with a series.
So the tool gives each registered metric one series, with the label value `x`, and has the registry gather and encode them.
The help text, the type and the histogram buckets come from the metric definitions.
Every value is set to 0, so the output is the same from run to run.

The type of a metric is the Go type of the collector that registers it, which the registry keeps in an unexported map.
The tool reads that map by reflection, so it is tied to the `client_golang` version in `go.mod`.
It stops with an error if it meets a collector it cannot give a series to.

## Limits

- Some registered metrics are left out on purpose.
  The list is the `exclusions` table in `main.go`, with a reason for each entry.
  The fixture header lists what was left out and why.
  Add an entry to the table to leave out another metric.
- Some wiring is done by hand in `registerAll`: the EC2NodeClass status controller and the AWS SDK metrics.
  A new object kind or operator-level registration in Karpenter is not listed until `registerAll` is updated.
  Comparing the output with the metrics page of the Karpenter docs catches this.
- The docs list `leader_election_slowpath_total`, but Karpenter never exposes it.
  controller-runtime declares the counter without registering it, so the tool leaves it out.
- "Registered" means that the metric is in the Prometheus registry that the tool asks.
  It does not mean that a deployment emits a series for it.
