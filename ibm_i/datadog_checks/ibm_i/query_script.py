# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys
from contextlib import closing

import pyodbc

from datadog_checks.base.utils.serialization import json


def query():
    connection = None

    for string in sys.stdin:
        if connection is None:
            connection_string = string.strip()
            try:
                connection = pyodbc.connect(connection_string)
            except Exception as e:
                print("{}".format(e), file=sys.stderr, flush=True)
                # Make the next query end immediately and fetch the error
                print('ENDOFQUERY', flush=True)
        else:
            query = string.strip()
            try:
                rows = []
                with closing(connection.execute(query)) as c:
                    rows = c.fetchall()

                for row in rows:
                    print(
                        json.dumps([item if item is None else str(item) for item in row]).decode("utf-8"),
                        flush=True,
                    )
            except Exception as e:
                print("{}".format(e), file=sys.stderr, flush=True)
            print('ENDOFQUERY', flush=True)
