# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Keep in sync with relevant fields from:
# https://github.com/DataDog/datadog-agent/blob/1fdb5e1746f9834d627f8fa1611d3753c1f9db10/pkg/process/config/data_scrubber.go#L14-L20
DEFAULT_BLACKLIST = (
    'access_token',
    'api_key',
    'apikey',
    'auth_token',
    'credentials',
    'passwd',
    'password',
    'secret',
    'stripetoken',
)
