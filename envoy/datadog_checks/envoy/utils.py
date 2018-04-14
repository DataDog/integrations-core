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
                tree['|_tags_|'] = sorted(
                    tree['|_tags_|'], key=lambda t: len(t), reverse=True
                )

    return metric_tree
