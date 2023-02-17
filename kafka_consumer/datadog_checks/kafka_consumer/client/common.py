from six import string_types


def validate_consumer_groups(consumer_groups):
    """Validate any explicitly specified consumer groups.

    consumer_groups = {'consumer_group': {'topic': [0, 1]}}
    """
    assert isinstance(consumer_groups, dict)
    for consumer_group, topics in consumer_groups.items():
        assert isinstance(consumer_group, string_types)
        assert isinstance(topics, dict) or topics is None  # topics are optional
        if topics is not None:
            for topic, partitions in topics.items():
                assert isinstance(topic, string_types)
                assert isinstance(partitions, (list, tuple)) or partitions is None  # partitions are optional
                if partitions is not None:
                    for partition in partitions:
                        assert isinstance(partition, int)
