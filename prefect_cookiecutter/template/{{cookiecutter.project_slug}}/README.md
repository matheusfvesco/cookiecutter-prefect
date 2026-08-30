# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

This project was generated from a small, flexible Prefect project template.
The directory names are starting points, not requirements. Rename or add
subdirectories to match the domain of the project.

## Getting Started

Install the project and its development dependencies with `uv`:

```bash
uv sync --extra dev
```

Run the included example flow locally:

```bash
uv run python -m src.workflows.flows.example_flow
```

Replace the example logic, task, and flow with the project implementation.

## Local Prefect Server

If a Prefect Server is not already running, start this ephemeral development
instance in a separate terminal:

For persistent development or shared environments, the recommended setup is a
Docker Compose deployment with PostgreSQL as the Prefect database. The command
below is only a quick local example and intentionally does not provide
persistent storage.

```bash
docker run --rm --name prefect-server \
  -p 4200:4200 \
  prefecthq/prefect:{{ cookiecutter.prefect_version }}-python{{ cookiecutter.python_version.split('.')[0] }}.{{ cookiecutter.python_version.split('.')[1] }} \
  prefect server start --host 0.0.0.0 --port 4200
```

This container uses temporary local storage. Its server data, deployments, and
flow-run history are lost when the container stops or is removed. It is only a
development example, not a persistent or production server.

In another terminal, point the Prefect CLI and worker at it:

```bash
export PREFECT_API_URL=http://127.0.0.1:4200/api
```

The Prefect UI is available at `http://127.0.0.1:4200`.

## Project Layout

- `src/logic/` contains reusable application or domain logic. Child packages
  can be organized by any project area, not only ETL or data processing.
- `src/schemas/` contains runtime schemas used to validate or serialize data
  crossing application boundaries.
- `src/workflows/common/` contains helpers shared by multiple workflows, such
  as configuration, integrations, clients, and common workflow utilities.
- `src/workflows/tasks/` contains Prefect tasks grouped by project area.
- `src/workflows/flows/` contains Prefect flows that compose tasks into runs.
- `tests/` separates common, logic, schema, Prefect, integration, validation,
  and regression tests.

## Prefect Deployments

`prefect.yaml` follows the structure created by `prefect init` using the
Docker-Git setup. The image name and tag are configured during project
generation. Edit the deployment entry under `deployments` when a flow is
ready to deploy, including its entrypoint and work pool name.

The file also contains a fully commented event-trigger example. It is
documentation only: it does not register an automation or emit an event.
Replace the example event name and payload mapping only when the project has a
real event producer and a deployment that should react to it.

### Deploying a Worker

Workers poll a Prefect work pool and start flow runs. The Docker-Git setup
expects a Docker work pool and a worker host with access to a Docker daemon.

```bash
# Create a Docker work pool once, or use an existing one.
uv run prefect work-pool create --type docker {{ cookiecutter.project_slug }}-pool

# Set the same pool name in prefect.yaml, then create the deployment.
uv run prefect deploy src/workflows/flows/example_flow.py:example_flow \
  --name example-flow \
  --pool {{ cookiecutter.project_slug }}-pool

# Start the worker on the machine that can run Docker containers.
uv run prefect worker start --pool {{ cookiecutter.project_slug }}-pool --type docker
```

Configure the Prefect API or log in to Prefect Cloud before starting the
worker. The pool name used by `prefect deploy`, `prefect.yaml`, and
`prefect worker start` must match. Run the worker as a long-running process or
service in the environment where flow runs should execute.

The deployment configuration includes Docker build and push steps. Configure
the image registry and credentials in the deployment environment before using
those steps in a remote environment.
