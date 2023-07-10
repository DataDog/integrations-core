# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urlparse


def initialize_instance(values, **kwargs):
    if 'openmetrics_endpoint' in values:
        validate_url(
            values['openmetrics_endpoint'],
            required_path='/metrics',
            example='http://localhost:2112/metrics',
            config='openmetrics_endpoint',
        )

    if 'weaviate_api_endpoint' in values:
        validate_url(
            values['weaviate_api_endpoint'],
            required_path=None,
            example='http://localhost:8080',
            config='weaviate_api_endpoint',
        )

    return values


def validate_url(url, required_path=None, example=None, config=None):
    # Validates the endpoint to ensure that the components are preents.
    # For OpenMetrics: Scheme, netloc and /metrics path
    # For API: Scheme, netloc and no path
    # Logs out troubleshooting errors and example
    url_parsed = urlparse(url)
    errors = []

    if not url_parsed.netloc:
        errors.append("couldn't properly parse endpoint")
    if not url_parsed.scheme:
        errors.append("http or https scheme is missing")
    if required_path and url_parsed.path != required_path:
        errors.append(f"URL should end with {required_path}")
    if not required_path and url_parsed.path:
        errors.append("should not contain a path or trailing /")

    if errors:
        error_message = ", ".join(errors)
        raise ValueError(
            f"{config}: {url} is incorrectly configured. Errors detected: {error_message}. Example: {example}"
        )
