# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

from datadog_checks.dev.tooling.datastructures import JSONDict

# This file contains the constants used for V2 manifest validator testing

ORACLE_METADATA_CSV_EXAMPLE = [(0, {"metric_name": "oracle.session_count"})]

V2_MANIFEST_ALL_PASS = JSONDict(
    {
        "app_id": "datadog-oracle",
        "assets": {
            "dashboards": {"oracle": "https://app.datadoghq.com/screen/integration/240/oracle-database---overview"},
            "integration": {
                "configuration": {"spec": "assets/configuration/spec.yaml"},
                "events": {"creates_events": True},
                "id": "oracle",
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "metrics_metadata.csv",
                    "prefix": "oracle.",
                },
                "service_checks": {"metadata_path": "assets/service_checks.json"},
                "source_type_name": "Oracle Database",
            },
        },
        "author": {
            "homepage": "https://www.datadoghq.com",
            "name": "Datadog",
            "sales_email": "help@datadoghq.com",
            "support_email": "help@datadoghq.com",
        },
        "display_on_public_website": True,
        "legal_terms": {},
        "manifest_version": "2.0.0",
        "oauth": {},
        "pricing": [{"billing_type": "free"}],
        "tile": {
            "changelog": "CHANGELOG.md",
            "classifier_tags": [
                "Category::Marketplace",
                "Category::Cloud",
                "Category::Log Collection",
                "Supported OS::Windows",
                "Supported OS::Mac OS",
                "Offering::Integration",
                "Offering::UI Extension",
            ],
            "configuration": "README.md#Setup",
            "description": "Oracle relational database system designed for enterprise grid computing",
            "media": [],
            "overview": "README.md#Overview",
            "title": "Oracle",
        },
    }
)

INCORRECT_MAINTAINER_MANIFEST = JSONDict(
    {
        "author": {
            "homepage": "https://www.datadoghq.com",
            "name": "Datadog",
            "sales_email": "help@datadoghq.com",
            "support_email": "stupidemail@fake.com",
        },
    }
)

INVALID_MAINTAINER_MANIFEST = JSONDict(
    {
        "author": {
            "homepage": "https://www.datadoghq.com",
            "name": "Datadog",
            "sales_email": "help@datadoghq.com",
            "support_email": "ǨĽŇŘŠŤŽ@invalid.com",
        },
    }
)

CORRECT_MAINTAINER_MANIFEST = JSONDict(
    {
        "author": {
            "homepage": "https://www.datadoghq.com",
            "name": "Datadog",
            "sales_email": "help@datadoghq.com",
            "support_email": "help@datadoghq.com",
        }
    }
)

FILE_EXISTS_NOT_IN_MANIFEST = JSONDict(
    {
        "assets": {
            "integration": {
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "",
                    "prefix": "oracle.",
                },
            },
        },
    }
)

FILE_IN_MANIFEST_DOES_NOT_EXIST = JSONDict(
    {
        "assets": {
            "integration": {
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "fake_metadata_file.csv",
                    "prefix": "oracle.",
                },
            },
        },
    }
)

CORRECT_METADATA_FILE_MANIFEST = JSONDict(
    {
        "assets": {
            "integration": {
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "metrics_metadata.csv",
                    "prefix": "oracle.",
                },
            },
        },
    }
)

CHECK_NOT_IN_METADATA_MANIFEST = JSONDict(
    {
        "assets": {
            "integration": {
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "metrics_metadata.csv",
                    "prefix": "oracle.",
                },
            },
        },
    }
)

CHECK_NOT_IN_MANIFEST = JSONDict(
    {
        "assets": {
            "integration": {
                "metrics": {
                    "auto_install": True,
                    "check": "",
                    "metadata_path": "metrics_metadata.csv",
                    "prefix": "oracle.",
                },
            },
        },
    }
)

CORRECT_CHECK_IN_METADATA_MANIFEST = JSONDict(
    {
        "assets": {
            "integration": {
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "metrics_metadata.csv",
                    "prefix": "oracle.",
                },
            },
        },
    }
)

HAS_LOGS_NO_TAG_MANIFEST = JSONDict(
    {
        "tile": {
            "classifier_tags": [
                "Category::Marketplace",
                "Offering::Integration",
                "Offering::UI Extension",
            ],
        },
    }
)

DISPLAY_ON_PUBLIC_INVALID_MANIFEST = JSONDict({"app_id": "datadog-oracle"})

DISPLAY_ON_PUBLIC_VALID_MANIFEST = JSONDict({"display_on_public_website": True})

IMMUTABLE_ATTRIBUTES_V1_MANIFEST = {"manifest_version": "1.0.0"}

IMMUTABLE_ATTRIBUTES_V2_MANIFEST = JSONDict({"manifest_version": "2.0.0"})

IMMUTABLE_ATTRIBUTES_PREV_MANIFEST_INVALID = json.dumps(
    {
        "app_id": "datadog-oracle",
        "assets": {
            "dashboards": {"oracle": "https://app.datadoghq.com/screen/integration/240/oracle-database---overview"},
            "monitors": {"cool-monitor": "link"},
            "integration": {
                "configuration": {"spec": "assets/configuration/spec.yaml"},
                "events": {"creates_events": True},
                "id": "oracle",
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "metrics_metadata.csv",
                    "prefix": "oracle.",
                },
                "service_checks": {"metadata_path": "assets/service_checks.json"},
                "source_type_name": "Oracle Database",
            },
        },
        "author": {
            "homepage": "https://www.datadoghq.com",
            "name": "Datadog",
            "sales_email": "help@datadoghq.com",
            "support_email": "help@datadoghq.com",
        },
        "display_on_public_website": True,
        "legal_terms": {},
        "manifest_version": "2.0.0",
        "oauth": {},
        "pricing": [{"billing_type": "free"}],
        "tile": {
            "changelog": "CHANGELOG.md",
            "classifier_tags": [
                "Category::Marketplace",
                "Category::Cloud",
                "Supported OS::Windows",
                "Supported OS::Mac OS",
                "Offering::Integration",
                "Offering::UI Extension",
            ],
            "configuration": "README.md#Setup",
            "description": "Oracle relational database system designed for enterprise grid computing",
            "media": [],
            "overview": "README.md#Overview",
            "title": "Oracle",
        },
    }
)

IMMUTABLE_ATTRIBUTES_CUR_MANIFEST_INVALID_SHORT_NAME = JSONDict(
    {
        "app_id": "datadog-oracle",
        "assets": {
            "dashboards": {"oracle": "https://app.datadoghq.com/screen/integration/240/oracle-dash"},
            "monitors": {"cool-monitor-dog": "link"},
            "integration": {
                "configuration": {"spec": "assets/configuration/spec.yaml"},
                "events": {"creates_events": True},
                "id": "oracle",
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "metrics_metadata.csv",
                    "prefix": "oracle.",
                },
                "service_checks": {"metadata_path": "assets/service_checks.json"},
                "source_type_name": "Oracle Database",
            },
        },
        "author": {
            "homepage": "https://www.datadoghq.com",
            "name": "Datadog",
            "sales_email": "help@datadoghq.com",
            "support_email": "help@datadoghq.com",
        },
        "display_on_public_website": True,
        "legal_terms": {},
        "manifest_version": "2.0.0",
        "oauth": {},
        "pricing": [{"billing_type": "free"}],
        "tile": {
            "changelog": "CHANGELOG.md",
            "classifier_tags": [
                "Category::Marketplace",
                "Category::Cloud",
                "Supported OS::Windows",
                "Supported OS::Mac OS",
                "Offering::Integration",
                "Offering::UI Extension",
            ],
            "configuration": "README.md#Setup",
            "description": "Oracle relational database system designed for enterprise grid computing",
            "media": [],
            "overview": "README.md#Overview",
            "title": "Oracle",
        },
    }
)

IMMUTABLE_ATTRIBUTES_CURRENT_MANIFEST_INVALID = JSONDict(
    {
        "app_id": "datadog-oracle-failure",
        "assets": {
            "dashboards": {"oracle": "https://app.datadoghq.com/screen/integration/240/oracle-database---overview"},
            "integration": {
                "configuration": {"spec": "assets/configuration/spec.yaml"},
                "events": {"creates_events": True},
                "id": "oracle",
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "metrics_metadata.csv",
                    "prefix": "oracle.",
                },
                "service_checks": {"metadata_path": "assets/service_checks.json"},
                "source_type_name": "Oracle Database",
            },
        },
        "author": {
            "homepage": "https://www.datadoghq.com",
            "name": "Datadog",
            "sales_email": "help@datadoghq.com",
            "support_email": "help@datadoghq.com",
        },
        "display_on_public_website": True,
        "legal_terms": {},
        "manifest_version": "2.0.0",
        "oauth": {},
        "pricing": [{"billing_type": "free"}],
        "tile": {
            "changelog": "CHANGELOG.md",
            "classifier_tags": [
                "Category::Marketplace",
                "Category::Cloud",
                "Supported OS::Windows",
                "Supported OS::Mac OS",
                "Offering::Integration",
                "Offering::UI Extension",
            ],
            "configuration": "README.md#Setup",
            "description": "Oracle relational database system designed for enterprise grid computing",
            "media": [],
            "overview": "README.md#Overview",
            "title": "Oracle",
        },
    }
)

IMMUTABLE_ATTRIBUTES_CURRENT_MANIFEST_VALID = JSONDict(
    {
        "app_id": "datadog-oracle",
        "assets": {
            "dashboards": {"oracle": "https://app.datadoghq.com/screen/integration/240/oracle-database---overview"},
            "monitors": {"cool-monitor": "link"},
            "integration": {
                "configuration": {"spec": "assets/configuration/spec.yaml"},
                "events": {"creates_events": True},
                "id": "oracle",
                "metrics": {
                    "auto_install": True,
                    "check": "oracle.session_count",
                    "metadata_path": "metrics_metadata.csv",
                    "prefix": "oracle.",
                },
                "service_checks": {"metadata_path": "assets/service_checks.json"},
                "source_type_name": "Oracle Database",
            },
        },
        "author": {
            "homepage": "https://www.datadoghq.com",
            "name": "Datadog",
            "sales_email": "help@datadoghq.com",
            "support_email": "help@datadoghq.com",
        },
        "display_on_public_website": True,
        "legal_terms": {},
        "manifest_version": "2.0.0",
        "oauth": {},
        "pricing": [{"billing_type": "free"}],
        "tile": {
            "changelog": "CHANGELOG.md",
            "classifier_tags": [
                "Category::Marketplace",
                "Category::Cloud",
                "Supported OS::Windows",
                "Supported OS::Mac OS",
                "Offering::Integration",
                "Offering::UI Extension",
            ],
            "configuration": "README.md#Setup",
            "description": "Oracle relational database system designed for enterprise grid computing",
            "media": [],
            "overview": "README.md#Overview",
            "title": "Oracle",
        },
    }
)


class MockedResponseInvalid:
    status_code = 400

    def raise_for_status(self):
        raise AssertionError()

    def json(self):
        return "Invalid response for test!"


class MockedResponseValid:
    status_code = 200

    def raise_for_status(self):
        return


class MockedContextObj:
    obj = {
        'org': 'my-org',
        'orgs': {
            'my-org': {
                'api_key': '123abc',
                'app_key': 'app123',
                'dd_url': 'foo.com',
            }
        },
    }
