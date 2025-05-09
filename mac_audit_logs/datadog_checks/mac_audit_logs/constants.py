# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
IPV4_PATTERN = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
TIMESTAMP_FORMAT = "%a %b %d %H:%M:%S %Y"
MIN_PORT = 0
MAX_PORT = 65535
MIN_COLLECTION_INTERVAL = 1
MAX_COLLECTION_INTERVAL = 64800
LOG_TEMPLATE = "MAC Audit Logs | MESSAGE={message}"
