# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import uuid

import click

from datadog_checks.dev.fs import write_file
from datadog_checks.dev.tooling.datastructures import JSONDict
from datadog_checks.dev.tooling.utils import get_manifest_file, get_valid_integrations, load_manifest

from ..console import CONTEXT_SETTINGS, abort, echo_info, echo_success

# This means the value is either not present in the old manifest, or there's logic needed to compute it
SKIP_IF_FOUND = "SKIP"

# Static text to let users know these values need updating by hand
TODO_FILL_IN = "TODO Please Fill In"

# Validate what manifest versions we can support and what we can upgrade from->to
SUPPORTED_MANIFEST_VERSIONS = ["1.0.0", "2.0.0"]
SUPPORTED_VERSION_UPGRADE_PATHS = {"1.0.0": ["2.0.0"]}

# JSONDict map all v2 fields to their v1 counterparts
# Skipping any fields that need manual intervention of custom logic
V2_TO_V1_MAP = JSONDict(
    {
        "/manifest_version": SKIP_IF_FOUND,
        "/app_id": "/integration_id",
        "/classifier_tags": [],
        "/display_on_public_website": "/is_public",
        "/tile": {},
        "/tile/overview": "README.md#Overview",
        "/tile/configuration": "README.md#Setup",
        "/tile/support": "README.md#Support",
        "/tile/changelog": "CHANGELOG.md",
        "/tile/description": "/short_description",
        "/tile/title": "/public_title",
        "/tile/media": [],
        "/author": {},
        "/author/homepage": "/author/homepage",
        "/author/name": "/author/name",
        "/author/support_email": "/maintainer",
        "/oauth": {},
        "/assets": {},
        "/assets/integration": {},
        "/assets/integration/source_type_name": "/display_name",
        "/assets/integration/configuration": {},
        "/assets/integration/configuration/spec": "/assets/configuration/spec",
        "/assets/integration/events": {},
        "/assets/integration/events/creates_events": "/creates_events",
        "/assets/integration/metrics": {},
        "/assets/integration/metrics/prefix": "/metric_prefix",
        "/assets/integration/metrics/check": "/metric_to_check",
        "/assets/integration/metrics/metadata_path": "/assets/metrics_metadata",
        "/assets/integration/service_checks": {},
        "/assets/integration/service_checks/metadata_path": "/assets/service_checks",
        "/assets/dashboards": "/assets/dashboards",
        "/assets/monitors": "/assets/monitors",
        "/assets/saved_views": "/assets/saved_views",
        "/assets/logs": "/assets/logs",
    }
)

OS_TO_CLASSIFIER_TAGS = {
    "linux": "Supported OS::Linux",
    "mac_os": "Supported OS::Mac OS",
    "windows": "Supported OS::Windows",
}

CATEGORIES_TO_CLASSIFIER_TAGS = {
    "alerting": "Category::Alerting",
    "autodiscovery": "Category::Autodiscovery",
    "automation": "Category::Automation",
    "aws": "Category::AWS",
    "azure": "Category::Azure",
    "caching": "Category::Caching",
    "cloud": "Category::Cloud",
    "collaboration": "Category::Collaboration",
    "compliance": "Category::Compliance",
    "configuration & deployment": "Category::Configuration Deployment",
    "containers": "Category::Containers",
    "cost management": "Category::Cost Management",
    "data store": "Category::Data Store",
    "developer tools": "Category::Developer Tools",
    "event management": "Category::Event Management",
    "exceptions": "Category::Exceptions",
    "google cloud": "Category::Google Cloud",
    "incidents": "Category::Incidents",
    "iot": "Category::IOT",
    "isp": "Category::ISP",
    "issue tracking": "Category::Issue Tracking",
    "languages": "Category::Languages",
    "log collection": "Category::Log Collection",
    "marketplace": "Category::Marketplace",
    "messaging": "Category::Messaging",
    "metrics": "Category::Metrics",
    "monitoring": "Category::Monitoring",
    "network": "Category::Network",
    "notification": "Category::Notification",
    "oracle": "Category::Oracle",
    "orchestration": "Category::Orchestration",
    "os & system": "Category::OS System",
    "processing": "Category::Processing",
    "profiling": "Category::Profiling",
    "provisioning": "Category::Provisioning",
    "security": "Category::Security",
    "snmp": "Category::SNMP",
    "source control": "Category::Source Control",
    "testing": "Category::Testing",
    "web": "Category::Web",
}


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manifest utilities')
def manifest():
    pass


@manifest.command(context_settings=CONTEXT_SETTINGS, short_help='Migrate a manifest to a newer schema version')
@click.argument('integration', required=True)
@click.argument('to_version', required=True)
@click.pass_context
def migrate(ctx, integration, to_version):
    """
    Helper tool to ease the migration of a manifest to a newer version, auto-filling fields when possible

    Inputs:

    integration: The name of the integration folder to perform the migration on

    to_version: The schema version to upgrade the manifest to
    """
    echo_info(f"Migrating {integration} manifest to {to_version}....", nl=True)

    # Perform input validations
    if integration and integration not in get_valid_integrations():
        abort(f'    Unknown integration `{integration}`, is your repo set properly in `ddev config`?')

    loaded_manifest = JSONDict(load_manifest(integration))
    manifest_version = loaded_manifest.get_path("/manifest_version")

    if to_version not in SUPPORTED_MANIFEST_VERSIONS:
        abort(f"    Unknown to_version: `{to_version}`. Valid options are: {SUPPORTED_MANIFEST_VERSIONS}")
    if to_version == manifest_version:
        abort(f"    {integration} is already on version `{manifest_version}`")
    if to_version not in SUPPORTED_VERSION_UPGRADE_PATHS.get(manifest_version, []):
        abort(
            f"    Can't migrate from version `{manifest_version}` to version: `{to_version}`. Unsupported upgrade path"
        )

    migrated_manifest = JSONDict()

    # Explicitly set the manifest_version first so it appears at the top of the manifest
    migrated_manifest.set_path("/manifest_version", "2.0.0")

    # Generate and introduce a uuid
    app_uuid = str(uuid.uuid4())
    migrated_manifest.set_path("/app_uuid", app_uuid)

    for key, val in V2_TO_V1_MAP.items():
        if val == SKIP_IF_FOUND:
            continue
        # If the value is a string and is a JSONPath, then load the value from the JSON Path
        elif isinstance(val, str) and val.startswith("/"):
            final_value = loaded_manifest.get_path(val)
        else:
            final_value = val

        # We need to remove any of the underlying "assets" that are just an empty dictionary
        if key in ["/assets/dashboards", "/assets/monitors", "/assets/saved_views"] and not final_value:
            continue

        if final_value is not None:
            migrated_manifest.set_path(key, final_value)

    # Update any previously skipped field in which we can use logic to assume the value of
    # Also iterate through any lists to include new/updated fields at each index of the list
    migrated_manifest.set_path("/classifier_tags", TODO_FILL_IN)

    # Retrieve and map all categories from other fields
    classifier_tags = []
    supported_os = loaded_manifest.get_path("/supported_os")
    for os in supported_os:
        os_tag = OS_TO_CLASSIFIER_TAGS.get(os.lower())
        if os_tag:
            classifier_tags.append(os_tag)

    categories = loaded_manifest.get_path("/categories")
    for category in categories:
        category_tag = CATEGORIES_TO_CLASSIFIER_TAGS.get(category.lower())
        if category_tag:
            classifier_tags.append(category_tag)

    # Write the manifest back to disk
    migrated_manifest.set_path("/classifier_tags", classifier_tags)

    # Marketplace-only fields:
    if ctx.obj['repo_name'] == "marketplace":
        migrated_manifest.set_path("/author/vendor_id", TODO_FILL_IN)
        migrated_manifest.set_path("/author/sales_email", loaded_manifest.get_path("/terms/legal_email"))

        migrated_manifest.set_path("/pricing", loaded_manifest.get_path("/pricing"))
        migrated_manifest.set_path("/legal_terms", {})
        migrated_manifest.set_path("/legal_terms/eula", loaded_manifest.get_path("/terms/eula"))

        for idx, _ in enumerate(migrated_manifest.get_path("/pricing") or []):
            migrated_manifest.set_path(f"/pricing/{idx}/product_id", TODO_FILL_IN)
            migrated_manifest.set_path(f"/pricing/{idx}/short_description", TODO_FILL_IN)
            migrated_manifest.set_path(f"/pricing/{idx}/includes_assets", True)

    write_file(get_manifest_file(integration), json.dumps(migrated_manifest, indent=2))

    echo_success(
        f"Successfully migrated {integration} manifest to version {to_version}. Please update any needed fields, "
        f"especially those that are marked with `{TODO_FILL_IN}`"
    )
