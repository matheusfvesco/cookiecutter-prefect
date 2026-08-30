from __future__ import annotations

import json
import re
from pathlib import Path

import click
from cookiecutter.main import cookiecutter

TEMPLATE_PATH = Path(__file__).parent / "template"
with (TEMPLATE_PATH / "cookiecutter.json").open(encoding="utf-8") as defaults_file:
    TEMPLATE_DEFAULTS = json.load(defaults_file)

DEFAULT_PROJECT_NAME = "prefect-project"
DEFAULT_DESCRIPTION = "A Prefect workflow project."
DEFAULT_PYTHON_VERSION = TEMPLATE_DEFAULTS["python_version"]
DEFAULT_PREFECT_VERSION = TEMPLATE_DEFAULTS["prefect_version"]


def project_slug(value: str) -> str:
    """Convert a project name into a simple Docker- and path-friendly slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise click.BadParameter("must contain at least one letter or number")
    return slug


def _value(value: str | None, prompt: str, default: str, no_input: bool) -> str:
    if value is not None:
        return value
    if no_input:
        return default
    return click.prompt(prompt, default=default)


@click.command()
@click.option("--project-name", help="Human-readable project name.")
@click.option("--description", help="Short project description.")
@click.option("--python-version", help="Python version for the generated project.")
@click.option("--prefect-version", help="Prefect version for the generated project.")
@click.option(
    "--image-name", help="Docker image name, including its registry if needed."
)
@click.option("--tag", "image_tag", help="Docker image tag.")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Directory in which to create the project.",
)
@click.option("--no-input", is_flag=True, help="Use defaults for omitted values.")
@click.option(
    "--overwrite-if-exists",
    is_flag=True,
    help="Allow Cookiecutter to write into an existing project directory.",
)
def main(
    project_name: str | None,
    description: str | None,
    python_version: str | None,
    prefect_version: str | None,
    image_name: str | None,
    image_tag: str | None,
    output_dir: Path,
    no_input: bool,
    overwrite_if_exists: bool,
) -> None:
    """Create a flexible Prefect project from this template."""
    project_name = _value(project_name, "Project name", DEFAULT_PROJECT_NAME, no_input)
    description = _value(
        description, "Project description", DEFAULT_DESCRIPTION, no_input
    )
    python_version = _value(
        python_version, "Python version", DEFAULT_PYTHON_VERSION, no_input
    )
    prefect_version = _value(
        prefect_version, "Prefect version", DEFAULT_PREFECT_VERSION, no_input
    )

    slug = project_slug(project_name)
    image_name = _value(image_name, "Docker image name", slug, no_input)
    image_tag = _value(image_tag, "Docker image tag", "latest", no_input)

    context = {
        "project_name": project_name,
        "project_slug": slug,
        "description": description,
        "python_version": python_version,
        "prefect_version": prefect_version,
        "image_name": image_name,
        "image_tag": image_tag,
    }

    generated_path = cookiecutter(
        str(TEMPLATE_PATH),
        no_input=True,
        extra_context=context,
        output_dir=str(output_dir),
        overwrite_if_exists=overwrite_if_exists,
    )
    click.echo(f"Created project at {generated_path}")
