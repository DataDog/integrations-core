# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


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
