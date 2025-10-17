# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
VALID_ECOSYSTEMS = ["pypi", "npm", "go", "github_action"]
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
GUARDDOG_ENVIRONMENT_PATH = "/opt/guarddog/guarddog-env/bin/guarddog"
GUARDDOG_COMMAND = GUARDDOG_ENVIRONMENT_PATH + " {package_ecosystem} verify {path} --output-format=json"
