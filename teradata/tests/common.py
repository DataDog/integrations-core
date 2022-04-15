# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK_NAME = 'teradata'

TERADATA_SERVER = os.environ.get('TERADATA_SERVER')
TERADATA_DD_USER = os.environ.get('TERADATA_DD_USER')
TERADATA_DD_PW = os.environ.get('TERADATA_DD_PW')

SERVICE_CHECK_CONNECT = 'teradata.can_connect'
SERVICE_CHECK_QUERY = 'teradata.can_query'

EXPECTED_TAGS = ["teradata_server:tdserver", "teradata_port:1025", "td_env:dev"]
