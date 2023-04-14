# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six.moves.urllib.parse import urlparse


def get_gitlab_version(http, log, gitlab_url, api_token):
    version = None

    try:
        if api_token is None:
            log.debug("GitLab token not found; please add one in your config to enable version metadata collection.")
            return

        response = http.get(
            "{}/api/v4/version".format(gitlab_url),
            params={'access_token': api_token},
        )

        version = response.json().get('version')
    except Exception as e:
        log.warning("GitLab version metadata not collected: %s", e)

    return version


def get_tags(instance):
    custom_tags = instance.get('tags', [])

    url = instance.get('gitlab_url')

    if not url:
        return custom_tags

    # creating tags for host and port
    parsed_url = urlparse(url)
    gitlab_host = parsed_url.hostname
    gitlab_port = 443 if parsed_url.scheme == 'https' else (parsed_url.port or 80)

    return ['gitlab_host:{}'.format(gitlab_host), 'gitlab_port:{}'.format(gitlab_port)] + custom_tags
