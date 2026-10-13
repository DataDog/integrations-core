# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Error code reported by PanosApiError when a response body is not parseable XML.
PARSE_ERROR_CODE = 'parse'

# `code` values PAN-OS uses for a rejected API key. 403 is lab-confirmed; 16 comes from the XML API error-codes doc
# and was never seen in the lab.
AUTH_ERROR_CODES = frozenset({'403', '16'})
