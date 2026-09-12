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

{% if cookiecutter.deployment_mode == "none" %}
## Prefect Server

This project does not generate Docker deployment artifacts. Configure the
Prefect CLI with an existing server at `{{ cookiecutter.prefect_server_url }}`.
{% else %}
## Deployment

The generated deployment targets `{{ cookiecutter.prefect_server_url }}` on port
`{{ cookiecutter.prefect_server_port }}` and uses the external Docker work pool
`{{ cookiecutter.work_pool_name }}`.

{% if cookiecutter.deployment_mode == "centralized" %}
`docker-compose.yml` is the application deployment helper. The Prefect server,
PostgreSQL database, and Docker worker are expected to be managed separately.
By default, the helper and flow-run containers expect a container named
`prefect-server` on the external `{{ cookiecutter.prefect_network_name }}` Docker
network and use `http://prefect-server:{{ cookiecutter.prefect_server_port }}/api`.
{% if cookiecutter.include_centralized_server_compose %}
The optional `docker-compose.server.yml` provides that server stack and creates
the named network. `Dockerfile.worker` builds the worker with the required
`prefect-docker` integration. Keep both files together if the server bundle is
moved to another directory or repository:

```bash
make server-up
```
The server, PostgreSQL, and worker services use `restart: unless-stopped`, so
they restart after a Docker daemon or host reboot. The PostgreSQL data is
stored in the named `prefect-postgres` volume; do not use `docker compose down
-v` unless you intend to delete it.
{% else %}
Create that network and attach the existing Prefect server container before
running `make deploy`. This project does not generate `Dockerfile.worker`
because the external server environment owns its worker image.
{% endif %}
If Prefect runs on another host or outside Docker, change
`PREFECT_CONTAINER_API_URL`, the deployment's `PREFECT_API_URL`, and its
`networks` job variable in `prefect.yaml` for that topology.
{% else %}
`docker-compose.yml` contains the application deployment helper, Prefect server,
PostgreSQL database, and Docker worker. `Dockerfile.worker` installs the
required `prefect-docker` integration with `uv`.

Start the standalone environment with:

```bash
make up
```
{% endif %}

Ensure the external work pool exists and register deployments with:

```bash
make create-pool
make deploy
```

`make create-pool` is safe to run again when the pool already exists. In
standalone mode, the worker also creates a missing pool automatically.

If a Prefect Server is not already running, use this temporary local server
without Compose as a development fallback:

```bash
docker run --rm --name prefect-server \
  -p {{ cookiecutter.prefect_server_port }}:{{ cookiecutter.prefect_server_port }} \
  prefecthq/prefect:{{ cookiecutter.prefect_version }}-python{{ cookiecutter.python_version.split('.')[0] }}.{{ cookiecutter.python_version.split('.')[1] }} \
  prefect server start --host 0.0.0.0 --port {{ cookiecutter.prefect_server_port }}
```

This container uses temporary local storage. Its server data, deployments, and
flow-run history are lost when the container stops or is removed. It is only a
development example, not a persistent or production server.

The Prefect UI is available at `http://127.0.0.1:{{ cookiecutter.prefect_server_port }}`.
{% endif %}

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

{% if cookiecutter.deployment_mode != "none" %}
## Prefect Deployments

`prefect.yaml` includes a runnable `example-flow` deployment whose code is
baked into the generated image. The image name and tag are configured during
project generation. Replace the example deployment as the project evolves.

The file also contains a fully commented event-trigger example. It is
documentation only: it does not register an automation or emit an event.
Replace the example event name and payload mapping only when the project has a
real event producer and a deployment that should react to it.

### Deploying a Worker

Workers poll a Prefect work pool and start flow runs. The Docker deployment
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

The default deployment builds an image on the Docker host used by the worker
and does not push it. If the worker uses another Docker host, add a Prefect
Docker push step, configure registry credentials, and change the image pull
policy to one appropriate for that registry.
{% endif %}
