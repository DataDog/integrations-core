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


def create_metric_from_partial(metric_dict, label_name, raw_metric_namespace, metric_family_name):
    # This method takes in the following:
    # metric_dict: dictionary containing {metric_type: [metric_names]}
    # label_name: the label name that the matching group will be assigned to
    # raw_metric_namespace: the common naming convention/namespace for the metric set as exposed on prometheus
    # metric_family_name: the non dynamic name of the metric family as exposed on prometheus
    # e.g: envoy_cluster_8443_fooBAZbarBUZ123456__bind_errors, envoy_cluster_8443_fooBAZbarBUZ123456__assignment_stale
    # raw_metric_namespace = envoy_cluster, metric_family_name = _bind_errors and _assignment_stale respectively
    ## TODO: add support for different regex patterns for the label regex
    metrics = {}

    for metric_type in metric_dict:
        for metric in metric_dict[metric_type]:
            if metric.endswith('_total'):
                metric = metric[:-6]
            if metric.startswith('_'):
                metric = metric[1:]

            metrics[rf"{raw_metric_namespace}_(.+)_{metric}$"] = {
                'label_name': label_name,
                'metric_type': metric_type,
                'new_name': f"{metric_family_name}.{metric}{'.count' if metric_type == 'count' else ''}",
            }
    return metrics
