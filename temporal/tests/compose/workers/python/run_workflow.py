# @@@SNIPSTART python-project-template-run-workflow
import asyncio

from run_worker import SayHello
from temporalio.client import Client


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("temporal:7233")

    # Execute a workflow
    result = await client.execute_workflow(
        SayHello.run, "Temporal", id="my-workflow-id", task_queue="python-task-queue"
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
