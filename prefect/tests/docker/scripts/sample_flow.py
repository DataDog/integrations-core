from prefect import flow, task


@task(name="add")
def add(a: int, b: int) -> int:
    return a + b


@task(name="multiply")
def multiply(a: int, b: int) -> int:
    return a * b


@flow(name="sample-flow")
def sample_flow(x: int = 1):
    add_result = add.submit(x, 2)
    multiply_result = multiply.submit(add_result, 10, wait_for=[add_result])
    print("Finished all tasks")
    return multiply_result


if __name__ == "__main__":
    sample_flow(3)
