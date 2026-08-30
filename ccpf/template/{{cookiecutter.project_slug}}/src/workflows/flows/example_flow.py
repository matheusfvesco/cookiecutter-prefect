"""Small example of a Prefect flow entrypoint."""

from prefect import flow

from src.workflows.tasks.etl_tasks.example_task import example_task


@flow
def example_flow(value: str = "example") -> str:
    """Compose tasks into a workflow run."""
    return example_task(value)


if __name__ == "__main__":
    example_flow()
