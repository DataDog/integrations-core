# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def mock():
    from snowflake import connector

    from .connector import connect

    connector.connect = connect
