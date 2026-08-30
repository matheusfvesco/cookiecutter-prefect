"""Small example of a Prefect task."""

from prefect import task

from src.logic.etl.example import identity


@task
def example_task(value: str) -> str:
    """Replace this example with one independently executable task."""
    return identity(value)
