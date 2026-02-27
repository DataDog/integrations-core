import time

from prefect import flow, task
from prefect.context import get_run_context


@task
def fail():
    raise RuntimeError("Intentional fail for testing")


@flow(retries=1, retry_delay_seconds=1, name="failing-flow")
def failing_flow():
    ctx = get_run_context()
    run_count = ctx.flow_run.run_count
    print(f"Run count: {run_count}")
    if run_count == 1:
        time.sleep(10)

    if run_count > 1:
        print("Retried")

    fail()


if __name__ == "__main__":
    failing_flow()
