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
    Normalization based on https://docs.paloaltonetworks.com/prisma/prisma-cloud/19-11/prisma-cloud-compute-edition-admin/api/porting_guide.html
    """  # noqa: E501
    for elem in data:
        if 'info' in elem and 'version' in elem['info']:
            elem['info']['scanVersion'] = elem['info']['version']
            del elem['info']['version']

        if 'info' in elem:
            if 'data' in elem['info']:
                elem.update(elem['info']['data'])
                del elem['info']['data']
            elem.update(elem['info'])
            del elem['info']

        for prev, new in NORMALIZATION_FIELDS.items():
            if prev in elem:
                elem[new] = elem[prev]
                del elem[prev]
