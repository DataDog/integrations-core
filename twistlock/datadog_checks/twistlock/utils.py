# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

NORMALIZATION_FIELDS = {
    "complianceVulnerabilities": "complianceIssues",
    "complianceVulnerabilitiesCnt": "complianceIssuesCount",
    "cveVulnerabilities": "vulnerabilities",
    "cveVulnerabilitiesCnt": "vulnerabilitiesCount",
    "cveVulnerabilityDistribution": "vulnerabilityDistribution",
    "pkgDistro": "osDistro",
    "pkgDistroRelease": "osDistroRelease",
}


def normalize_api_data_inplace(data):
    """
    Normalize api data to make it compatible with both standalone Twistlock and Prisma Cloud Twistlock.
    Normalization based on:
    https://docs.paloaltonetworks.com/prisma/prisma-cloud/19-11/prisma-cloud-compute-edition-admin/api/porting_guide.html
    """
    for elem in data:
        if 'info' in elem:
            info = elem.pop('info')
            if 'version' in info:
                info['scanVersion'] = info.pop('version')
            if 'data' in info:
                elem.update(info.pop('data'))
            elem.update(info)

        for old, new in NORMALIZATION_FIELDS.items():
            if old in elem:
                elem[new] = elem.pop(old)
