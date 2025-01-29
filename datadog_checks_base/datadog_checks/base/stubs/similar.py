from difflib import SequenceMatcher

from datadog_checks.base.stubs.common import HistogramBucketStub, MetricStub, ServiceCheckStub

'''
Build similar message for better test assertion failure message.
'''

MAX_SIMILAR_TO_DISPLAY = 15


def dict_diff(expected, closest):
    """
    Returns an array of key/value pairs that are different between the two dicts.
    """
    diff = []
    for key in closest.keys() | expected.keys():
        expected_value = expected.get(key)
        closest_value = closest.get(key)

        if expected_value is not None and expected_value != closest_value:
            diff.append((key, expected_value, closest_value))

    return diff


def tags_list_to_dict(tags):
    return {tag.split(':', 1)[0]: (tag.split(':', 1)[1] if ":" in tag else '') for tag in tags}


def tags_diff(expected, closest):
    """
    Returns an array of key/value pairs that are different between the two lists of tags.
    """
    diff = []
    expected_tags_dict = tags_list_to_dict(expected)
    closest_tags_dict = tags_list_to_dict(closest)
    for tag in expected_tags_dict:
        if expected_tags_dict[tag] != closest_tags_dict.get(tag):
            diff.append((tag, expected_tags_dict[tag], closest_tags_dict.get(tag)))
    for tag in closest_tags_dict:
        if tag not in expected_tags_dict:
            diff.append((tag, None, closest_tags_dict[tag]))
    return diff


def format_metric_stub_diff(expected, closest):
    """
    Return formatted difference between expected and closest metric stubs
    """
    diff = []

    closest_dict = closest._asdict()
    expected_dict = expected._asdict()
    dict_diffs = dict_diff(expected_dict, closest_dict)
    for key, expected_value, closest_value in dict_diffs:
        if key == "tags":
            tag_diffs = tags_diff(expected_value, closest_value)
            for tag, expected_tag_value, closest_tag_value in tag_diffs:
                diff.append(
                    f"        Expected tag {tag}:{expected_tag_value}\n" + f"        Found {tag}:{closest_tag_value}"
                )
        else:
            diff.append(f"        Expected {key}: {expected_value}\n        Found {closest_value}")
    return diff


def build_similar_elements_msg(expected, submitted_elements):
    """
    Return formatted similar elements (metrics, service checks) received compared to submitted elements
    """

    similar_metrics = _build_similar_elements(expected, submitted_elements)
    similar_metrics_to_print = []

    for score, metric_stub in similar_metrics[:MAX_SIMILAR_TO_DISPLAY]:
        if metric_stub.tags:
            metric_stub.tags.sort()
        similar_metrics_to_print.append("{:.2f}    {}".format(score, metric_stub))

    closest_diff = []
    if similar_metrics:
        [_, closest] = similar_metrics[0]
        closest_diff = format_metric_stub_diff(expected, closest)

    return (
        "Expected:\n"
        + "        {}\n".format(expected)
        + "Difference to closest:\n"
        + "\n".join(closest_diff)
        + "\n\n"
        + "Similar submitted:\n"
        + "Score   Most similar\n"
        + "\n".join(similar_metrics_to_print)
    )


def _build_similar_elements(expected_element, submitted_elements):
    """
    Return similar elements (metrics, service checks) received compared to the submitted elements
    """
    if isinstance(expected_element, MetricStub):
        scoring_fn = _get_similarity_score_for_metric
    elif isinstance(expected_element, ServiceCheckStub):
        scoring_fn = _get_similarity_score_for_service_check
    elif isinstance(expected_element, HistogramBucketStub):
        scoring_fn = _get_similarity_score_for_histogram_bucket
    else:
        raise NotImplementedError("Invalid type: {}".format(expected_element))

    similar_elements = []
    for _, metric_stubs in submitted_elements.items():
        for candidate_metric in metric_stubs:
            score = scoring_fn(expected_element, candidate_metric)
            similar_elements.append((score, candidate_metric))
    return sorted(similar_elements, reverse=True)


def _get_similarity_score_for_metric(expected_metric, candidate_metric):
    # Tuple of (score, weight)
    scores = [(_is_similar_text_score(expected_metric.name, candidate_metric.name), 3)]

    if expected_metric.type is not None:
        score = 1 if expected_metric.type == candidate_metric.type else 0
        scores.append((score, 1))

    if expected_metric.tags is not None:
        score = _is_similar_text_score(str(sorted(expected_metric.tags)), str(sorted(candidate_metric.tags)))
        scores.append((score, 1))

    if expected_metric.value is not None:
        score = 1 if expected_metric.value == candidate_metric.value else 0
        scores.append((score, 1))

    if expected_metric.hostname:
        score = _is_similar_text_score(expected_metric.hostname, candidate_metric.hostname)
        scores.append((score, 1))

    if expected_metric.device:
        # device is only present in metrics coming from the real agent in e2e tests
        score = _is_similar_text_score(expected_metric.device, candidate_metric.device)
        scores.append((score, 1))

    return _compute_score(scores)


def _get_similarity_score_for_service_check(expected_service_check, candidate_service_check):
    # Tuple of (score, weight)
    scores = [(_is_similar_text_score(expected_service_check.name, candidate_service_check.name), 3)]

    if expected_service_check.status is not None:
        score = 1 if expected_service_check.status == candidate_service_check.status else 0
        scores.append((score, 1))

    if expected_service_check.tags is not None:
        score = _is_similar_text_score(
            str(sorted(expected_service_check.tags)), str(sorted(candidate_service_check.tags))
        )
        scores.append((score, 1))

    if expected_service_check.hostname:
        score = _is_similar_text_score(expected_service_check.hostname, candidate_service_check.hostname)
        scores.append((score, 1))

    if expected_service_check.message:
        score = _is_similar_text_score(expected_service_check.message, candidate_service_check.message)
        scores.append((score, 1))

    return _compute_score(scores)


def _get_similarity_score_for_histogram_bucket(expected_histogram_bucket, candidate_histogram_bucket):
    # Tuple of (score, weight)
    scores = [(_is_similar_text_score(expected_histogram_bucket.name, candidate_histogram_bucket.name), 3)]

    if expected_histogram_bucket.value is not None:
        score = 1 if expected_histogram_bucket.value == candidate_histogram_bucket.value else 0
        scores.append((score, 1))

    if expected_histogram_bucket.lower_bound is not None:
        score = 1 if expected_histogram_bucket.lower_bound == candidate_histogram_bucket.lower_bound else 0
        scores.append((score, 1))

    if expected_histogram_bucket.upper_bound is not None:
        score = 1 if expected_histogram_bucket.upper_bound == candidate_histogram_bucket.upper_bound else 0
        scores.append((score, 1))

    if expected_histogram_bucket.monotonic is not None:
        score = 1 if expected_histogram_bucket.monotonic == candidate_histogram_bucket.monotonic else 0
        scores.append((score, 1))

    if expected_histogram_bucket.tags is not None:
        score = _is_similar_text_score(
            str(sorted(expected_histogram_bucket.tags)), str(sorted(candidate_histogram_bucket.tags))
        )
        scores.append((score, 1))

    if expected_histogram_bucket.hostname:
        score = _is_similar_text_score(expected_histogram_bucket.hostname, candidate_histogram_bucket.hostname)
        scores.append((score, 1))

    return _compute_score(scores)


def _compute_score(scores):
    score_total = 0
    weight_total = 0

    for score, weight in scores:
        score_total += score * weight
        weight_total += weight

    return score_total / weight_total


def _is_similar_text_score(a, b):
    if b is None:
        return 0
    return SequenceMatcher(None, a, b).ratio()
