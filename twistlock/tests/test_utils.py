# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.twistlock.utils import normalize_api_data_inplace


def test_normalize_api_data_inplace():
    data = [
        {
            "scanTime": "2019-02-14T16:14:15.843Z",
            'info': {
                'id': 'sha256:08c927f8524a28fb8b76f369a89b2570eb6b92ba5b758dc1a87c6cf5256bf0cc',
                'cveVulnerabilities': [{"text": "", "id": 46, "severity": "low"}],
                'data': {
                    "binaries": [
                        {
                            "name": "bash",
                            "path": "/bin/bash",
                            "md5": "ac56f4b8fac5739ccdb45777d313becf",
                            "cveCount": 104,
                            "layerTime": 0,
                        },
                    ]
                },
                'complianceVulnerabilities': [],
                "complianceVulnerabilitiesCnt": 1,
                "cveVulnerabilitiesCnt": 64,
                "cveVulnerabilityDistribution": 64,
                "pkgDistro": "debian",
                "pkgDistroRelease": "stretch",
                "version": "18.11.103",
            },
        },
    ]

    expected_data = [
        {
            "scanTime": "2019-02-14T16:14:15.843Z",
            'id': 'sha256:08c927f8524a28fb8b76f369a89b2570eb6b92ba5b758dc1a87c6cf5256bf0cc',
            'vulnerabilities': [{"text": "", "id": 46, "severity": "low"}],
            "binaries": [
                {
                    "name": "bash",
                    "path": "/bin/bash",
                    "md5": "ac56f4b8fac5739ccdb45777d313becf",
                    "cveCount": 104,
                    "layerTime": 0,
                },
            ],
            'complianceIssues': [],
            'complianceIssuesCount': 1,
            "vulnerabilitiesCount": 64,
            "vulnerabilityDistribution": 64,
            "osDistro": "debian",
            "osDistroRelease": "stretch",
            "scanVersion": "18.11.103",
        },
    ]

    normalize_api_data_inplace(data)

    assert expected_data == data
