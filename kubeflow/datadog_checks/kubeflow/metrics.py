# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Some metrics mapping are too long. This turns off the 120 line limit for this file:
# ruff: noqa: E501


METRIC_MAP = {
    'katib_controller_reconcile_count': 'katib.controller.reconcile',
    'katib_controller_reconcile_duration_seconds': 'katib.controller.reconcile.duration.seconds',
    'katib_experiment_created': 'katib.experiment.created',
    'katib_experiment_duration_seconds': 'katib.experiment.duration.seconds',
    'katib_experiment_failed': 'katib.experiment.failed',
    'katib_experiment_running_total': 'katib.experiment.running.total',
    'katib_experiment_succeeded': 'katib.experiment.succeeded',
    'katib_suggestion_created': 'katib.suggestion.created',
    'katib_suggestion_duration_seconds': 'katib.suggestion.duration.seconds',
    'katib_suggestion_failed': 'katib.suggestion.failed',
    'katib_suggestion_running_total': 'katib.suggestion.running.total',
    'katib_suggestion_succeeded': 'katib.suggestion.succeeded',
    'katib_trial_created': 'katib.trial.created',
    'katib_trial_duration_seconds': 'katib.trial.duration.seconds',
    'katib_trial_failed': 'katib.trial.failed',
    'katib_trial_running_total': 'katib.trial.running.total',
    'katib_trial_succeeded': 'katib.trial.succeeded',
    'kserve_inference_duration_seconds': 'kserve.inference.duration.seconds',
    'kserve_inference_errors': 'kserve.inference.errors',
    'kserve_inference_request_bytes': 'kserve.inference.request.bytes',
    'kserve_inference_response_bytes': 'kserve.inference.response.bytes',
    'kserve_inferences': 'kserve.inferences',
    'notebook_server_created': 'notebook.server.created',
    'notebook_server_failed': 'notebook.server.failed',
    'notebook_server_reconcile_count': 'notebook.server.reconcile',
    'notebook_server_reconcile_duration_seconds': 'notebook.server.reconcile.duration.seconds',
    'notebook_server_running_total': 'notebook.server.running.total',
    'notebook_server_succeeded': 'notebook.server.succeeded',
    'pipeline_run_duration_seconds': 'pipeline.run.duration.seconds',
    'pipeline_run_status': 'pipeline.run.status',
}

RENAME_LABELS_MAP = {
    'version': 'go_version',
}
