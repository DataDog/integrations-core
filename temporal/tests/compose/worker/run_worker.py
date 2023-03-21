# @@@SNIPSTART python-project-template-run-worker
import asyncio
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig
from temporalio.worker import Worker


@activity.defn
async def say_hello(name: str) -> str:
    return f"Hello, {name}!"


@workflow.defn
class SayHello:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(say_hello, name, schedule_to_close_timeout=timedelta(seconds=5))


async def main():
    new_runtime = Runtime(telemetry=TelemetryConfig(metrics=PrometheusConfig(bind_address="0.0.0.0:8002")))
    client = await Client.connect("temporal:7233", namespace="default", runtime=new_runtime)
    # Run the worker
    worker = Worker(client, task_queue="python-task-queue", workflows=[SayHello], activities=[say_hello])
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
