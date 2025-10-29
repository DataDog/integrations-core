# Couchbase Integration Scripts

## generate_metrics_code.py

Generates `datadog_checks/couchbase/metrics_generated.py` from `metadata.csv`.

### Usage

From the couchbase integration directory:

```bash
python scripts/generate_metrics_code.py < metadata.csv > datadog_checks/couchbase/metrics_generated.py
```

### When to Run

Run this script after updating `metadata.csv` with:
- New Prometheus metrics
- Corrected metric types
- Updated metric metadata

### What It Does

The script:
1. Reads metric definitions from `metadata.csv` (via stdin)
2. Extracts metric names and types
3. Strips the `couchbase.` namespace prefix
4. Generates Python code with a `METRIC_DATA` list
5. Outputs to stdout (typically redirected to `metrics_generated.py`)

### Output Format

The generated file contains `METRIC_DATA`, a list of dictionaries with:
- `metric_name`: Metric name without the `couchbase.` prefix (e.g., `cm.uuid_cache_max_items`)
- `metric_type`: One of: `gauge`, `counter`, or `histogram`

This data is used by `metrics.py` to:
- Generate metric name mappings (Couchbase raw names → Datadog names)
- Create type overrides (fix Couchbase's missing/incorrect Prometheus TYPE metadata)
- Handle histogram metrics (_bucket, _count, _sum suffixes)

### Example

```bash
# After curating metadata.csv
python scripts/generate_metrics_code.py < metadata.csv > datadog_checks/couchbase/metrics_generated.py

# Verify the output
python -c "from datadog_checks.couchbase.metrics_generated import METRIC_DATA; print(f'{len(METRIC_DATA)} metrics')"
```
