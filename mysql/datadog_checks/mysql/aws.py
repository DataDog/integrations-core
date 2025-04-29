# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import boto3


def generate_rds_iam_token(host, port, username, region, role_arn=None):
    if role_arn:
        # when role_arn is defined, assume the role to generate the token
        # this can be used for cross-account access
        sts_client = boto3.client("sts")
        assumed_role = sts_client.assume_role(RoleArn=role_arn, RoleSessionName="datadog-rds-iam-auth-session")
        credentials = assumed_role["Credentials"]
        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region,
        )
    else:
        session = boto3.Session(region_name=region)
    client = session.client("rds")
    token = client.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=username)

    return token
