from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import click
from cookiecutter.main import cookiecutter

TEMPLATE_PATH = Path(__file__).parent / "template"
with (TEMPLATE_PATH / "cookiecutter.json").open(encoding="utf-8") as defaults_file:
    TEMPLATE_DEFAULTS = json.load(defaults_file)

DEFAULT_PROJECT_NAME = "prefect-project"
DEFAULT_DESCRIPTION = "A Prefect workflow project."
DEFAULT_PYTHON_VERSION = TEMPLATE_DEFAULTS["python_version"]
DEFAULT_PREFECT_VERSION = TEMPLATE_DEFAULTS["prefect_version"]
DEFAULT_DEPLOYMENT_MODE = TEMPLATE_DEFAULTS["deployment_mode"]
DEFAULT_PREFECT_SERVER_URL = TEMPLATE_DEFAULTS["prefect_server_url"]


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


def _deployment_mode(value: str | None, no_input: bool) -> str:
    if value is not None:
        return click.Choice(["none", "centralized", "standalone"]).convert(
            value, None, None
        )
    if no_input:
        return DEFAULT_DEPLOYMENT_MODE
    return click.prompt(
        "Deployment mode",
        type=click.Choice(["none", "centralized", "standalone"]),
        default=DEFAULT_DEPLOYMENT_MODE,
    )


def _python_version(value: str) -> str:
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", value):
        raise click.BadParameter(
            "must be a numeric major.minor or major.minor.patch version",
            param_hint="--python-version",
        )
    return value


def _prefect_version(value: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise click.BadParameter(
            "must be a numeric major.minor.patch version",
            param_hint="--prefect-version",
        )
    return value


def _server_endpoint(value: str) -> tuple[str, int]:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise click.BadParameter(
            "must be an http(s) URL with a hostname and port",
            param_hint="--prefect-server-url",
        )
    try:
        port = parsed.port
    except ValueError as error:
        raise click.BadParameter(
            "must use a numeric port between 1 and 65535",
            param_hint="--prefect-server-url",
        ) from error
    if port is None or not 1 <= port <= 65535:
        raise click.BadParameter(
            "must use a port between 1 and 65535",
            param_hint="--prefect-server-url",
        )
    return value, port


def _container_server_url(value: str, port: int) -> str:
    parsed = urlsplit(value)
    if parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        return parsed._replace(netloc=f"host.docker.internal:{port}").geturl()
    return value


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
    "--deployment-mode",
    type=click.Choice(["none", "centralized", "standalone"]),
    help="Deployment packaging mode.",
)
@click.option(
    "--prefect-server-url",
    help="Prefect API URL, including its port.",
)
@click.option(
    "--include-centralized-server-compose",
    is_flag=True,
    help="Generate the optional centralized Prefect server Compose stack.",
)
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
    deployment_mode: str | None,
    prefect_server_url: str | None,
    include_centralized_server_compose: bool,
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
    python_version = _python_version(python_version)
    prefect_version = _value(
        prefect_version, "Prefect version", DEFAULT_PREFECT_VERSION, no_input
    )
    prefect_version = _prefect_version(prefect_version)

    slug = project_slug(project_name)
    image_name = _value(image_name, "Docker image name", slug, no_input)
    image_tag = _value(image_tag, "Docker image tag", "latest", no_input)
    deployment_mode = _deployment_mode(deployment_mode, no_input)
    prefect_server_url = _value(
        prefect_server_url,
        "Prefect server URL",
        DEFAULT_PREFECT_SERVER_URL,
        no_input,
    )
    prefect_server_url, prefect_server_port = _server_endpoint(prefect_server_url)

    if deployment_mode == "centralized":
        if not include_centralized_server_compose and not no_input:
            include_centralized_server_compose = click.confirm(
                "Generate docker-compose.server.yml?", default=False
            )
    elif include_centralized_server_compose:
        raise click.UsageError(
            "--include-centralized-server-compose is only valid for centralized mode"
        )

    context = {
        "project_name": project_name,
        "project_slug": slug,
        "description": description,
        "python_version": python_version,
        "prefect_version": prefect_version,
        "image_name": image_name,
        "image_tag": image_tag,
        "deployment_mode": deployment_mode,
        "prefect_server_url": prefect_server_url,
        "prefect_container_server_url": _container_server_url(
            prefect_server_url, prefect_server_port
        ),
        "prefect_server_port": prefect_server_port,
        "include_centralized_server_compose": include_centralized_server_compose,
        "work_pool_name": "local-docker-pool",
        "prefect_network_name": "prefect-server-network",
    }

    destination = output_dir / slug
    if destination.exists():
        click.echo(
            f"Warning: {destination} already exists; existing data may be lost.",
            err=True,
        )

    generated_path = cookiecutter(
        str(TEMPLATE_PATH),
        no_input=True,
        extra_context=context,
        output_dir=str(output_dir),
        overwrite_if_exists=overwrite_if_exists,
    )
    click.echo(f"Created project at {generated_path}")
