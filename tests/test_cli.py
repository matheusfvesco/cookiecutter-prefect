import importlib
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from ccpf.cli import TEMPLATE_PATH, main, project_slug


def render_project(tmp_path: Path, *args: str) -> Path:
    output_dir = tmp_path / "output"
    result = CliRunner().invoke(
        main,
        ["--no-input", "--output-dir", str(output_dir), *args],
    )
    assert result.exit_code == 0, result.output
    return output_dir / "prefect-project"


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
    deployment = parsed["deployments"][0]
    assert deployment["name"] == "example-flow"
    assert deployment["entrypoint"] == (
        "src/workflows/flows/example_flow.py:example_flow"
    )
    assert parsed["push"] == []
    assert parsed["pull"] == []
    assert "# deployments:" in prefect_yaml
    assert "#           - your.domain.event" in prefect_yaml
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


@pytest.mark.parametrize(
    ("args", "present", "absent"),
    [
        (
            ("--deployment-mode", "none"),
            ("prefect.yaml",),
            (
                ".dockerignore",
                "Dockerfile",
                "Dockerfile.worker",
                "Makefile",
                "docker-compose.yml",
                "docker-compose.server.yml",
            ),
        ),
        (
            ("--deployment-mode", "centralized"),
            (
                ".dockerignore",
                "Dockerfile",
                "Makefile",
                "docker-compose.yml",
                "prefect.yaml",
            ),
            ("Dockerfile.worker", "docker-compose.server.yml"),
        ),
        (
            (
                "--deployment-mode",
                "centralized",
                "--include-centralized-server-compose",
            ),
            (
                "Dockerfile",
                "Dockerfile.worker",
                ".dockerignore",
                "Makefile",
                "docker-compose.yml",
                "docker-compose.server.yml",
                "prefect.yaml",
            ),
            (),
        ),
        (
            ("--deployment-mode", "standalone"),
            (
                ".dockerignore",
                "Dockerfile",
                "Dockerfile.worker",
                "Makefile",
                "docker-compose.yml",
                "prefect.yaml",
            ),
            ("docker-compose.server.yml",),
        ),
    ],
)
def test_deployment_artifact_matrix(
    tmp_path: Path,
    args: tuple[str, ...],
    present: tuple[str, ...],
    absent: tuple[str, ...],
) -> None:
    project_dir = render_project(tmp_path, *args)

    for filename in present:
        assert (project_dir / filename).is_file(), filename
    for filename in absent:
        assert not (project_dir / filename).exists(), filename


def test_omitted_mode_defaults_to_centralized(tmp_path: Path) -> None:
    project_dir = render_project(tmp_path)

    assert (project_dir / "docker-compose.yml").is_file()
    assert (project_dir / "Dockerfile").is_file()
    assert not (project_dir / "docker-compose.server.yml").exists()


@pytest.mark.parametrize(
    "url",
    [
        "localhost:4200/api",
        "http://localhost/api",
        "http://localhost:0/api",
        "http://localhost:65536/api",
    ],
)
def test_invalid_prefect_server_url_fails_before_rendering(
    tmp_path: Path, url: str
) -> None:
    result = CliRunner().invoke(
        main,
        [
            "--no-input",
            "--prefect-server-url",
            url,
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert not (tmp_path / "prefect-project").exists()


def test_centralized_application_compose_is_independent_of_server_stack(
    tmp_path: Path,
) -> None:
    without_server = render_project(
        tmp_path / "without-server", "--deployment-mode", "centralized"
    )
    with_server = render_project(
        tmp_path / "with-server",
        "--deployment-mode",
        "centralized",
        "--include-centralized-server-compose",
    )

    assert (without_server / "docker-compose.yml").read_text() == (
        with_server / "docker-compose.yml"
    ).read_text()


def test_compose_topology_and_endpoint_propagation(tmp_path: Path) -> None:
    project_dir = render_project(
        tmp_path,
        "--deployment-mode",
        "standalone",
        "--prefect-server-url",
        "http://prefect.example.test:5420/api",
    )

    compose = yaml.safe_load((project_dir / "docker-compose.yml").read_text())
    prefect = yaml.safe_load((project_dir / "prefect.yaml").read_text())
    services = compose["services"]

    assert {"deploy", "prefect-server", "postgres", "prefect-worker"} <= services.keys()
    assert services["deploy"].get("restart") is None
    assert services["prefect-server"]["restart"] == "unless-stopped"
    assert services["postgres"]["restart"] == "unless-stopped"
    assert services["prefect-worker"]["restart"] == "unless-stopped"
    assert compose["volumes"] == {"prefect-postgres": None}
    assert services["prefect-server"]["ports"] == ["5420:5420"]
    assert services["prefect-server"]["environment"]["PREFECT_SERVER_UI_API_URL"] == (
        "http://prefect.example.test:5420/api"
    )
    assert "5420/api" in services["prefect-worker"]["environment"]["PREFECT_API_URL"]
    assert compose["networks"]["prefect-network"]["name"] == (
        "prefect-server-network"
    )
    assert prefect["deployments"][0]["work_pool"]["name"] == "prefect-project-pool"
    job_variables = prefect["deployments"][0]["work_pool"]["job_variables"]
    assert prefect["deployments"][0]["entrypoint"] == (
        "src/workflows/flows/example_flow.py:example_flow"
    )
    assert prefect["push"] == []
    assert prefect["pull"] == []
    assert job_variables["image_pull_policy"] == "Never"
    assert job_variables["networks"] == ["prefect-server-network"]
    assert job_variables["env"]["PREFECT_API_URL"] == (
        "http://prefect-server:5420/api"
    )
    assert (
        prefect["deployments"][0]["work_pool"]["job_variables"]["env"]["PREFECT_SERVER_PORT"]
        == "5420"
    )
    assert "5420" in (project_dir / ".env.example").read_text()
    assert "5420" in (project_dir / "Makefile").read_text()
    assert "5420" in (project_dir / "README.md").read_text()


def test_server_compose_contains_prefect_infrastructure(tmp_path: Path) -> None:
    project_dir = render_project(
        tmp_path,
        "--deployment-mode",
        "centralized",
        "--include-centralized-server-compose",
    )

    server = yaml.safe_load((project_dir / "docker-compose.server.yml").read_text())
    assert {"prefect-server", "postgres", "prefect-worker"} <= server[
        "services"
    ].keys()
    assert "healthcheck" in server["services"]["prefect-server"]
    assert "/var/run/docker.sock:/var/run/docker.sock" in server["services"][
        "prefect-worker"
    ]["volumes"]
    worker = server["services"]["prefect-worker"]
    assert worker["build"] == {"context": ".", "dockerfile": "Dockerfile.worker"}
    assert worker["restart"] == "unless-stopped"
    assert server["services"]["prefect-server"]["restart"] == "unless-stopped"
    assert server["services"]["postgres"]["restart"] == "unless-stopped"
    assert server["volumes"] == {"prefect-postgres": None}


def test_centralized_containers_use_shared_network_and_uv(tmp_path: Path) -> None:
    project_dir = render_project(tmp_path, "--deployment-mode", "centralized")

    compose = yaml.safe_load((project_dir / "docker-compose.yml").read_text())
    prefect = yaml.safe_load((project_dir / "prefect.yaml").read_text())
    deploy = compose["services"]["deploy"]
    job_variables = prefect["deployments"][0]["work_pool"]["job_variables"]

    assert deploy["environment"]["PREFECT_API_URL"] == (
        "${PREFECT_CONTAINER_API_URL:-http://prefect-server:4200/api}"
    )
    assert deploy["networks"] == ["prefect-network"]
    assert compose["networks"]["prefect-network"] == {
        "name": "prefect-server-network",
        "external": True,
    }
    assert job_variables["env"]["PREFECT_API_URL"] == (
        "http://prefect-server:4200/api"
    )
    assert job_variables["networks"] == ["prefect-server-network"]
    assert deploy["command"][:4] == ["uv", "run", "--isolated", "--with-editable"]

    dockerfile = (project_dir / "Dockerfile").read_text()
    assert "RUN uv sync --no-dev" in dockerfile
    assert "pip install" not in dockerfile

    makefile = (project_dir / "Makefile").read_text()
    assert "PREFECT_CONTAINER_API_URL=$(PREFECT_CONTAINER_API_URL)" in makefile
    assert "server-up:" not in makefile
    assert "server-down:" not in makefile


def test_centralized_external_api_url_keeps_service_dns_default(
    tmp_path: Path,
) -> None:
    project_dir = render_project(
        tmp_path,
        "--deployment-mode",
        "centralized",
        "--prefect-server-url",
        "https://prefect.example.test:8443/api",
    )

    compose = yaml.safe_load((project_dir / "docker-compose.yml").read_text())
    assert compose["services"]["deploy"]["environment"]["PREFECT_API_URL"] == (
        "${PREFECT_CONTAINER_API_URL:-http://prefect-server:8443/api}"
    )
    prefect = yaml.safe_load((project_dir / "prefect.yaml").read_text())
    assert prefect["deployments"][0]["work_pool"]["job_variables"]["env"][
        "PREFECT_API_URL"
    ] == "http://prefect-server:8443/api"


def test_centralized_server_make_targets_follow_optional_compose(
    tmp_path: Path,
) -> None:
    project_dir = render_project(
        tmp_path,
        "--deployment-mode",
        "centralized",
        "--include-centralized-server-compose",
    )

    makefile = (project_dir / "Makefile").read_text()
    assert "server-up:" in makefile
    assert "server-down:" in makefile

    server = yaml.safe_load((project_dir / "docker-compose.server.yml").read_text())
    assert server["networks"]["prefect-network"]["name"] == (
        "prefect-server-network"
    )

    worker_dockerfile = (project_dir / "Dockerfile.worker").read_text()
    assert 'uv pip install --system "prefect[docker]==3.8.4"' in worker_dockerfile
    assert "RUN pip install" not in worker_dockerfile


def test_readme_preserves_project_sections_and_changes_deployment_section(
    tmp_path: Path,
) -> None:
    for mode in ("none", "centralized", "standalone"):
        project_dir = render_project(
            tmp_path / mode, "--deployment-mode", mode
        )
        readme = (project_dir / "README.md").read_text()

        assert "## Getting Started" in readme
        assert "## Project Layout" in readme
        assert "<!-- deployment:" not in readme
        if mode == "none":
            assert "docker-compose.yml" not in readme
        elif mode == "standalone":
            assert "contains the application deployment helper" in readme
            assert "docker-compose.server.yml" not in readme
        else:
            assert "docker-compose.yml" in readme


def test_centralized_follow_up_prompt_is_only_interactive_centralized(
    tmp_path: Path,
) -> None:
    centralized = CliRunner().invoke(
        main,
        [
            "--project-name",
            "Centralized",
            "--deployment-mode",
            "centralized",
            "--output-dir",
            str(tmp_path / "centralized"),
        ],
        input="\n" * 7,
    )
    standalone = CliRunner().invoke(
        main,
        [
            "--project-name",
            "Standalone",
            "--deployment-mode",
            "standalone",
            "--output-dir",
            str(tmp_path / "standalone"),
        ],
        input="\n" * 6,
    )

    assert centralized.exit_code == 0, centralized.output
    assert "Generate docker-compose.server.yml?" in centralized.output
    assert standalone.exit_code == 0, standalone.output
    assert "Generate docker-compose.server.yml?" not in standalone.output


def test_packaged_template_contains_deployment_candidates() -> None:
    project_template = TEMPLATE_PATH / "{{cookiecutter.project_slug}}"

    for filename in (
        "Dockerfile",
        "Dockerfile.worker",
        ".dockerignore",
        "Makefile",
        "docker-compose.yml",
        "docker-compose.server.yml",
        ".env.example",
    ):
        assert (project_template / filename).is_file(), filename
    assert (TEMPLATE_PATH / "hooks/post_gen_project.py").is_file()
