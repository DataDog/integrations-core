# generate

A program to generate the `metadata.csv` and metric name mapping required by the
`cockroachdb` Datadog integration.

## Usage

Build the `generate` program.

```
go build .
```

Download the `metrics.html` from
https://github.com/cockroachdb/cockroach/blob/master/docs/generated/metrics/metrics.html.

Run the generator against the `metrics.html` file.

```
generate metrics.html
```

A `metadata.csv` and `mapping.txt` file is generated in your current working
directory.

Replace `cockroachdb/metadata.csv` with the generated `metadata.csv` file.

Update the `METRIC_MAP` in `cockroachdb/datadog_checks/cockroachdb/metrics.py`
with the content from `mapping.txt`.
