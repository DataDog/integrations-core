# ABOUTME: Endpoint paths and constants for the NiFi REST API.
# ABOUTME: Centralized definitions used by the API client and check.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

ABOUT_ENDPOINT = '/flow/about'
ACCESS_TOKEN_ENDPOINT = '/access/token'
CLUSTER_SUMMARY_ENDPOINT = '/flow/cluster/summary'
SYSTEM_DIAGNOSTICS_ENDPOINT = '/system-diagnostics'
FLOW_STATUS_ENDPOINT = '/flow/status'
PROCESS_GROUP_STATUS_ENDPOINT = '/flow/process-groups/{}/status'
BULLETIN_BOARD_ENDPOINT = '/flow/bulletin-board'

BULLETIN_LEVEL_ORDER = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3}
