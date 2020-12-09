# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import semver

SOURCE_TYPE_NAME = "Cloud Foundry"
MAX_LOOKBACK_SECONDS = 600
TOCKEN_EXPIRATION_BUFFER = 300
UAA_SERVICE_CHECK_NAME = "uaa.can_authenticate"
API_SERVICE_CHECK_NAME = "api.can_connect"
MAX_PAGE_SIZE_V3 = 5000
MAX_PAGE_SIZE_V2 = 100
DEFAULT_PAGE_SIZE = 100
DEFAULT_EVENT_FILTER = ["audit.app.restage", "audit.app.update", "audit.app.create", "app.crash"]
MIN_V3_VERSION = semver.VersionInfo(major=3, minor=78, patch=0)
