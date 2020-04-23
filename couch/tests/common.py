# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import re

from datadog_checks.base.utils.common import get_docker_hostname

CHECK_NAME = "couch"
CHECK_ID = 'test:123'

PORT = "5984"
HOST = get_docker_hostname()
URL = "http://{}:{}".format(HOST, PORT)
USER = "dduser"
PASSWORD = "pawprint"

HERE = os.path.dirname(os.path.abspath(__file__))

COUCH_RAW_VERSION = os.getenv('COUCH_VERSION')
COUCH_MAJOR_VERSION = int(re.split(r'\D+', COUCH_RAW_VERSION)[0])

# Publicly readable databases
DB_NAMES = ["_replicator", "_users", "kennel"]

GLOBAL_GAUGES = [
    "couchdb.couchdb.auth_cache_hits",
    "couchdb.couchdb.auth_cache_misses",
    "couchdb.httpd.requests",
    "couchdb.httpd_request_methods.GET",
    "couchdb.httpd_request_methods.PUT",
    "couchdb.couchdb.request_time",
    "couchdb.couchdb.open_os_files",
    "couchdb.couchdb.open_databases",
    "couchdb.httpd_status_codes.200",
    "couchdb.httpd_status_codes.201",
    "couchdb.httpd_status_codes.400",
    "couchdb.httpd_status_codes.401",
    "couchdb.httpd_status_codes.404",
]

CHECK_GAUGES = ["couchdb.by_db.disk_size", "couchdb.by_db.doc_count"]

BASIC_CONFIG = {"server": URL}

BASIC_CONFIG_V2 = {"server": URL, "user": "dduser", "password": "pawprint"}

BASIC_CONFIG_TAGS = ["instance:{}".format(URL)]

BAD_CONFIG = {"server": "http://localhost:11111"}

BAD_CONFIG_TAGS = ["instance:http://localhost:11111"]

NODE1 = {"server": URL, "user": USER, "password": PASSWORD, "name": "couchdb@couchdb-0.docker.com"}

NODE2 = {"server": URL, "user": USER, "password": PASSWORD, "name": "couchdb@couchdb-1.docker.com"}

NODE3 = {"server": URL, "user": USER, "password": PASSWORD, "name": "couchdb@couchdb-2.docker.com"}

ALL_NODES = [NODE1, NODE2, NODE3]
