# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import boto3


def generate_rds_iam_token(host, port, username, region):
    session = boto3.Session(region_name=region)
    client = session.client("rds")
    token = client.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=username)

    return token
