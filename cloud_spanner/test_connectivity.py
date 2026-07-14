#!/usr/bin/env python3
# Connectivity smoke test — no agent, no metric submission.
# Connects to a real Spanner instance and prints rows from QUERY_STATS_TOP_MINUTE.
#
# Usage:
#   GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json \
#   python test_connectivity.py <project_id> <instance_id> <database>
#
# Or with a credentials file explicitly:
#   python test_connectivity.py <project_id> <instance_id> <database> --credentials /path/to/key.json

import argparse
import sys

QUERY = """
SELECT
  INTERVAL_END,
  REQUEST_TAG,
  QUERY_TYPE,
  TEXT,
  EXECUTION_COUNT,
  AVG_LATENCY_SECONDS,
  AVG_CPU_SECONDS
FROM SPANNER_SYS.QUERY_STATS_TOP_MINUTE
ORDER BY INTERVAL_END DESC, AVG_CPU_SECONDS DESC
LIMIT 20
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project_id')
    parser.add_argument('instance_id')
    parser.add_argument('database')
    parser.add_argument('--credentials', help='Path to service account JSON key file')
    args = parser.parse_args()

    try:
        from google.cloud import spanner
    except ImportError:
        print("ERROR: google-cloud-spanner not installed. Run: pip install google-cloud-spanner")
        sys.exit(1)

    print(f"Connecting to projects/{args.project_id}/instances/{args.instance_id}/databases/{args.database} ...")

    kwargs = {'project': args.project_id}
    if args.credentials:
        from google.oauth2 import service_account

        kwargs['credentials'] = service_account.Credentials.from_service_account_file(
            args.credentials,
            scopes=['https://www.googleapis.com/auth/cloud-platform'],
        )

    client = spanner.Client(**kwargs)
    instance = client.instance(args.instance_id)
    database = instance.database(args.database)

    print("Connection established. Querying SPANNER_SYS.QUERY_STATS_TOP_MINUTE ...")

    with database.snapshot() as snapshot:
        rows = list(snapshot.execute_sql(QUERY))

    if not rows:
        print(
            "Connected successfully — no rows in QUERY_STATS_TOP_MINUTE yet"
            " (the table populates after ~1 minute of query activity)."
        )
        return

    print(f"\nFound {len(rows)} row(s):\n")
    fmt = "{:<26} {:<20} {:<20} {:>10} {:>16} {:>14}"
    print(fmt.format("INTERVAL_END", "REQUEST_TAG", "QUERY_TYPE", "EXEC_COUNT", "AVG_LATENCY_S", "AVG_CPU_S"))
    print("-" * 110)
    for row in rows:
        interval_end, request_tag, query_type, text, exec_count, avg_latency, avg_cpu = row
        print(
            fmt.format(
                str(interval_end)[:26],
                (request_tag or '')[:20],
                (query_type or '')[:20],
                exec_count,
                f"{avg_latency:.6f}",
                f"{avg_cpu:.6f}",
            )
        )
        print(f"  SQL: {(text or '')[:120]}")


if __name__ == '__main__':
    main()
