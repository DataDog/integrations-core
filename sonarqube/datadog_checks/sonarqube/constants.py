# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# <WEB_ENDPOINT>/api/metrics/types
NUMERIC_TYPES = {'BOOL', 'FLOAT', 'INT', 'PERCENT', 'RATING'}

# All `domain` attributes found in: <WEB_ENDPOINT>/api/metrics/search
CATEGORIES = {
    'Complexity': 'complexity',
    'Coverage': 'coverage',
    'Documentation': 'documentation',
    'Duplications': 'duplications',
    'General': 'general',
    'Issues': 'issues',
    'Maintainability': 'maintainability',
    'Management': 'management',
    'Releasability': 'releasability',
    'Reliability': 'reliability',
    'SCM': 'scm',
    'Security': 'security',
    'SecurityReview': 'security_review',
    'Size': 'size',
}
