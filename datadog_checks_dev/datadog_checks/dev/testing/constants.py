# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# If a file changes in a PR with any of these file extensions,
# a test will run against the check containing the file
TESTABLE_FILE_PATTERNS = ('*.py', '*.ini', '*.in', '*.txt', '*.yml', '*.yaml', '**/tests/*')
NON_TESTABLE_FILES = ('auto_conf.yaml', 'agent_requirements.in')
REQUIREMENTS_IN = 'requirements.in'
