# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.tooling.datastructures import JSONDict

# This file contains the constants used for V2 manifest validator testing

ORACLE_METADATA_CSV_EXAMPLE = [(0, {"metric_name": "oracle.session_count"})]

V2_VALID_MANIFEST = {
    "app_id": "datadog-oracle",
    "assets": {
        "dashboards": {"oracle": "assets/dashboards/example.json"},
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
        "configuration": "README.md#Setup",
        "description": "Oracle relational database system designed for enterprise grid",
        "media": [],
        "overview": "README.md#Overview",
        "title": "Oracle",
        "classifier_tags": [
            "Category::Marketplace",
            "Category::Cloud",
            "Category::Log Collection",
            "Supported OS::Windows",
            "Supported OS::macOS",
            "Offering::Integration",
            "Offering::UI Extension",
        ],
    },
}

VALID_MEDIA_MANIFEST = JSONDict(
    {
        "tile": {
            "media": [
                {
                    "media_type": "video",
                    "caption": "This is an example video caption!",
                    "image_url": "images/video_thumbnail.png",
                    "vimeo_id": 123456789,
                },
                {
                    "media_type": "image",
                    "caption": "This is an example image caption!",
                    "image_url": "images/acme_before.png",
                },
                {
                    "media_type": "image",
                    "caption": "This is an example image caption!",
                    "image_url": "images/acme_after.png",
                },
            ]
        }
    }
)

INVALID_MEDIA_MANIFEST_TOO_MANY_VIDEOS = JSONDict(
    {
        "tile": {
            "media": [
                {
                    "media_type": "video",
                    "caption": "This is an example video caption!",
                    "image_url": "images/video_thumbnail.png",
                    "vimeo_id": 123456789,
                },
                {
                    "media_type": "video",
                    "caption": "This is an example video caption!",
                    "image_url": "images/acme_before.png",
                    "vimeo_id": 123456789,
                },
            ]
        }
    }
)

INVALID_MEDIA_MANIFEST_BAD_STRUCTURE = JSONDict(
    {
        "tile": {
            "media": [
                {
                    "media_type": "video",
                    "cation": "This is an example video caption!",
                    "imageurl": "images/video_thumbnail.png",
                    "vimeo_id": 123456789,
                },
                {
                    "meda_type": "image",
                    "captin": "This is an example image caption!",
                    "image_url": "images/acme_before.png",
                },
            ]
        }
    }
)

INVALID_MEDIA_MANIFEST_INCORRECT_VIMEO_ID_TYPE = JSONDict(
    {
        "tile": {
            "media": [
                {
                    "media_type": "video",
                    "cation": "This is an example video caption!",
                    "image_url": "images/video_thumbnail.png",
                    "vimeo_id": "123456789",
                },
                {
                    "media_type": "image",
                    "caption": "This is an example image caption!",
                    "image_url": "images/acme_before.png",
                },
            ]
        }
    }
)

IMMUTABLE_ATTRIBUTES_V1_MANIFEST = {"manifest_version": "1.0.0"}

IMMUTABLE_ATTRIBUTES_V2_MANIFEST = JSONDict({"manifest_version": "2.0.0"})

VALID_TILE_DESCRIPTION_V2_MANIFEST = JSONDict({"tile": {"description": "This is a valid length tile description!"}})

INVALID_TILE_DESCRIPTION_V2_MANIFEST = JSONDict(
    {
        "tile": {
            "description": "This description is way too long to be valid! It will be cut off when displayed in the UI."
        }
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
