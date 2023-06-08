from difflib import SequenceMatcher

from six import iteritems

from datadog_checks.base.stubs.common import HistogramBucketStub, MetricStub, ServiceCheckStub

'''
Build similar message for better test assertion failure message.
'''

MAX_SIMILAR_TO_DISPLAY = 15


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

    return (
        "Expected:\n"
        + "        {}\n".format(expected)
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
    for _, metric_stubs in iteritems(submitted_elements):
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
