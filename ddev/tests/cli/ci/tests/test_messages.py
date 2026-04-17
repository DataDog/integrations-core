# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, FailedCheck, TestBatch, UpdatePRComment, WorkflowStatus
from ddev.event_bus.orchestrator import BaseMessage


class TestBatchJob:
    def test_default_instantiation(self):
        job = BatchJob()
        assert job.name == ""
        assert job.target == ""
        assert job.runner == ""
        assert job.environment == ""
        assert job.platform == ""
        assert job.unit_tests is False
        assert job.e2e_tests is False

    def test_explicit_instantiation(self):
        job = BatchJob(
            name="postgres-py3.13",
            target="postgres",
            runner="ubuntu-22.04",
            environment="py3.13-15",
            platform="linux",
            unit_tests=True,
            e2e_tests=True,
        )
        assert job.name == "postgres-py3.13"
        assert job.target == "postgres"
        assert job.runner == "ubuntu-22.04"
        assert job.environment == "py3.13-15"
        assert job.platform == "linux"
        assert job.unit_tests is True
        assert job.e2e_tests is True


class TestFailedCheck:
    def test_default_instantiation(self):
        check = FailedCheck()
        assert check.name == ""
        assert check.url == ""

    def test_explicit_instantiation(self):
        check = FailedCheck(name="Postgres-py3.13-9.6-UTF8", url="https://github.com/actions/runs/123")
        assert check.name == "Postgres-py3.13-9.6-UTF8"
        assert check.url == "https://github.com/actions/runs/123"


class TestWorkflowStatus:
    def test_default_instantiation(self):
        status = WorkflowStatus()
        assert status.url == ""
        assert status.id == 0
        assert status.success_count is None
        assert status.failed_count is None
        assert status.failed_checks == []

    def test_explicit_instantiation(self):
        checks = [FailedCheck(name="Check1", url="https://example.com/1")]
        status = WorkflowStatus(
            url="https://github.com/actions/runs/42",
            id=42,
            success_count=10,
            failed_count=1,
            failed_checks=checks,
        )
        assert status.url == "https://github.com/actions/runs/42"
        assert status.id == 42
        assert status.success_count == 10
        assert status.failed_count == 1
        assert status.failed_checks == checks


class TestTestBatch:
    def test_is_base_message_subclass(self):
        assert issubclass(TestBatch, BaseMessage)

    def test_instantiation_with_id_only(self):
        msg = TestBatch(id="batch-1")
        assert msg.id == "batch-1"
        assert msg.job_list == []
        assert msg.jobs_count == 0
        assert msg.integrations == []

    def test_explicit_instantiation(self):
        jobs = [BatchJob(name="postgres-py3.13", target="postgres")]
        msg = TestBatch(
            id="batch-2",
            job_list=jobs,
            jobs_count=1,
            integrations=["postgres"],
        )
        assert msg.id == "batch-2"
        assert msg.job_list == jobs
        assert msg.jobs_count == 1
        assert msg.integrations == ["postgres"]


class TestBatchFinished:
    def test_is_base_message_subclass(self):
        assert issubclass(BatchFinished, BaseMessage)

    def test_instantiation_with_id_only(self):
        msg = BatchFinished(id="finished-1")
        assert msg.id == "finished-1"
        assert msg.status == ""
        assert msg.run_id == 0
        assert msg.workflow_url == ""
        assert msg.artifacts_path == ""

    def test_explicit_instantiation(self):
        msg = BatchFinished(
            id="finished-2",
            status="success",
            run_id=98765,
            workflow_url="https://github.com/actions/runs/98765",
            artifacts_path="/tmp/artifacts/98765",
        )
        assert msg.id == "finished-2"
        assert msg.status == "success"
        assert msg.run_id == 98765
        assert msg.workflow_url == "https://github.com/actions/runs/98765"
        assert msg.artifacts_path == "/tmp/artifacts/98765"


class TestUpdatePRComment:
    def test_is_base_message_subclass(self):
        assert issubclass(UpdatePRComment, BaseMessage)

    def test_instantiation_with_id_only(self):
        msg = UpdatePRComment(id="pr-update-1")
        assert msg.id == "pr-update-1"
        assert msg.done is False
        assert msg.workflows == []

    def test_explicit_instantiation(self):
        workflows = [
            WorkflowStatus(
                url="https://github.com/actions/runs/1",
                id=1,
                success_count=5,
                failed_count=0,
                failed_checks=[],
            )
        ]
        msg = UpdatePRComment(id="pr-update-2", done=True, workflows=workflows)
        assert msg.id == "pr-update-2"
        assert msg.done is True
        assert msg.workflows == workflows

    def test_workflow_with_failed_checks(self):
        checks = [
            FailedCheck(name="Redis-py3.12-7.0", url="https://github.com/actions/runs/2/jobs/10"),
            FailedCheck(name="Redis-py3.11-6.2", url="https://github.com/actions/runs/2/jobs/11"),
        ]
        workflows = [WorkflowStatus(id=2, failed_count=2, failed_checks=checks)]
        msg = UpdatePRComment(id="pr-update-3", workflows=workflows)
        assert len(msg.workflows[0].failed_checks) == 2
        assert msg.workflows[0].failed_checks[0].name == "Redis-py3.12-7.0"
