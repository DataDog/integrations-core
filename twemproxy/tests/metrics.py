# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
GLOBAL_STATS = {'curr_connections', 'total_connections'}

POOL_STATS = {'client_connections', 'server_ejects'}

POOL_STATS_2 = {'client_eof', 'client_err', 'forward_error', 'fragments'}

SERVER_STATS = {'server_connections', 'server_timedout'}

SERVER_STATS_2 = {
    'in_queue',
    'out_queue',
    'in_queue_bytes',
    'out_queue_bytes',
    'server_err',
    'server_eof',
    'requests',
    'request_bytes',
    'responses',
    'response_bytes',
}
