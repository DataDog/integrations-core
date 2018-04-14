from collections import defaultdict


def tree():
    return defaultdict(tree)


def make_metric_tree(metrics):
    metric_tree = tree()

    for metric in metrics:
        # We make `mapping` reference the root of the tree
        # at every iteration to create the new branches.
        mapping = metric_tree

        # Separate each full metric name into its constituent parts.
        parts = metric.split('.')

        for i, part in enumerate(parts):
            tags = metrics[metric]['tags'][i]
            num_tags = len(tags)

            # We'll create keys as they are referenced. See:
            # https://en.wikipedia.org/wiki/Autovivification
            mapping = mapping[part]
            mapping['tag_length_map'][num_tags] = tags

            # Pre-compute the minimum number of tags it will take
            # for the parser to proceed to the subsequent part.
            minumum_num_tags = mapping.get('minumum_num_tags', 0)
            if num_tags < minumum_num_tags:
                mapping['minumum_num_tags'] = num_tags

    return metric_tree
