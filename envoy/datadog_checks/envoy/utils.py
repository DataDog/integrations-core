# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re

import requests

LEGACY_VERSION_RE = re.compile(r'/(\d\.\d\.\d)/')


def make_metric_tree(metrics):
    metric_tree = {}

    for metric in metrics:
        # We make `tree` reference the root of the tree
        # at every iteration to create the new branches.
        tree = metric_tree

        # Separate each full metric name into its constituent parts.
        parts = metric.split('.')

        for i, part in enumerate(parts):
            # Create branch if necessary.
            if part not in tree:
                tree[part] = {}

            # Move to the next branch.
            tree = tree[part]

            # Create a list for our possible tag configurations if necessary.
            if '|_tags_|' not in tree:
                tree['|_tags_|'] = []

            # Get the tag configuration for the current branch's metric part.
            tags = metrics[metric]['tags'][i]

            # Ensure the tag configuration doesn't already exist.
            if tags not in tree['|_tags_|']:
                # Each metric part can be proceeded by a differing number of tags.
                tree['|_tags_|'].append(tags)

                # Sort possible tag configurations by length in reverse order.
                tree['|_tags_|'] = sorted(tree['|_tags_|'], key=lambda t: len(t), reverse=True)

    return metric_tree


def _get_server_info(server_info_url, log, http):
    raw_version = None
    try:
        response = http.get(server_info_url)
        if response.status_code != 200:
            msg = 'Envoy endpoint `{}` responded with HTTP status code {}'.format(server_info_url, response.status_code)
            log.info(msg)
            return None
        # {
        #   "version": "222aaacccfff888/1.14.1/Clean/RELEASE/BoringSSL",
        #   "state": "LIVE",
        #   ...
        # }
        try:
            raw_version = response.json()["version"].split('/')[1]
        except Exception as e:
            log.debug('Error decoding json for url=`%s`. Error: %s', server_info_url, str(e))

        if raw_version is None:
            # Search version in server info for Envoy version <= 1.8
            # Example:
            #     envoy 5d25f466c3410c0dfa735d7d4358beb76b2da507/1.8.0/Clean/RELEASE live 581130 581130 0
            content = response.content.decode()
            found = LEGACY_VERSION_RE.search(content)
            log.debug('Looking for version in content: %s', content)
            if found:
                raw_version = found.group(1)
            else:
                log.debug('Version not matched.')
                return

    except requests.exceptions.Timeout:
        log.warning('Envoy endpoint `%s` timed out after %s seconds', server_info_url, http.options['timeout'])
        return None
    except Exception as e:
        log.warning('Error collecting Envoy version with url=`%s`. Error: %s', server_info_url, str(e))
        return None

    return raw_version


def modify_metrics_dict(metrics):
    # This function removes the wildcard from the metric list defined in metrics.py. Parser.py compares the compiled
    # metric with the metrics lists and if the entry is not found, it will raise an UnknowMetric error. Since the "*."
    # is used for wildcard matching, the comparison will always be false. E.g.:
    # "*.http_local_rate_limit.enabled" =/= "http_local_rate_limit.enabled
    # This is needed for metrics that start with a configurable namespace such as:
    # `<stat_prefix>.http_local_rate_limit.enabled` and parsed as http_local_rate_limit.enabled with tag
    # `stat_prefix=<stat_prefix>` in the parser.py
    mod_metrics_dict = {}

    for key, value in metrics.items():
        new_key = key.replace('*.', '')
        mod_metrics_dict[new_key] = value

    return mod_metrics_dict
