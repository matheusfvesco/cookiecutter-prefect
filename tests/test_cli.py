import importlib
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from ccpf.cli import main, project_slug


def test_project_slug_is_generic_and_path_safe() -> None:
    assert project_slug("My Little Project") == "my-little-project"
    assert project_slug("my_little_project") == "my-little-project"


def test_cli_renders_custom_project_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = CliRunner().invoke(
        main,
        [
            "--no-input",
            "--project-name",
            "Example Project",
            "--description",
            "A generic project description.",
            "--python-version",
            "3.12.2",
            "--prefect-version",
            "3.8.3",
            "--image-name",
            "registry/example-project",
            "--tag",
            "development",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    project_dir = tmp_path / "example-project"
    assert project_dir.is_dir()
    assert (project_dir / "src/workflows/flows/example_flow.py").is_file()
    assert (project_dir / "scripts/.gitkeep").is_file()

    project_config = (project_dir / "pyproject.toml").read_text()
    assert 'requires-python = ">=3.12.2"' in project_config
    assert '"prefect>=3.8.3"' in project_config
    assert '"prefect-docker>=0.3.1"' in project_config

    prefect_yaml = (project_dir / "prefect.yaml").read_text()
    parsed = yaml.safe_load(prefect_yaml)
    assert parsed["prefect-version"] == "3.8.3"

    build = parsed["build"][0]["prefect_docker.deployments.steps.build_docker_image"]
    assert build["image_name"] == "registry/example-project"
    assert build["tag"] == "development"
    assert parsed["deployments"][0]["name"] is None
    assert "# deployments:" in prefect_yaml
    assert "#           - your.domain.event" in prefect_yaml
    assert "'{{ repository }}'" in prefect_yaml
    assert "'{{ build_image.image }}'" in prefect_yaml
    assert '"{{ event.payload.value }}"' in prefect_yaml

    project_readme = (project_dir / "README.md").read_text()
    assert "If a Prefect Server is not already running" in project_readme
    assert "-p 4200:4200" in project_readme
    assert "temporary local storage" in project_readme
    assert "prefecthq/prefect:3.8.3-python3.12" in project_readme

    task_source = (
        project_dir / "src/workflows/tasks/etl_tasks/example_task.py"
    ).read_text()
    assert "from src.logic.etl.example import identity" in task_source
    assert "return identity(value)" in task_source

    flow_source = (project_dir / "src/workflows/flows/example_flow.py").read_text()
    assert (
        "from src.workflows.tasks.etl_tasks.example_task import example_task"
        in flow_source
    )
    assert "return example_task(value)" in flow_source

    monkeypatch.syspath_prepend(str(project_dir))
    task_module = importlib.import_module("src.workflows.tasks.etl_tasks.example_task")
    assert task_module.example_task.fn("through-the-task") == "through-the-task"


def test_cli_help_is_available() -> None:
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Docker image name" in result.output
