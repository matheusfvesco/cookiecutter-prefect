# Cookiecutter Prefect

A small Cookiecutter template for starting flexible Prefect projects.

The structure is based on the shared organization found in the example
Prefect repositories under `examples_structure/`. It provides extension points
for reusable logic, schemas, workflow helpers, Prefect tasks, flows, model or
algorithm families, and several categories of tests without assuming a
particular business domain.

The directory names in the generated project are starting points. For
example, `src/logic/etl/` can be renamed to `src/logic/data_scraping/`,
`src/logic/my_domain/`, or any other project-specific area.

## Quickstart

Clone the repository and install the CLI as a local `uv` tool:

```bash
git clone https://github.com/matheusfvesco/cookiecutter-prefect.git
cd cookiecutter-prefect
uv tool install .
```

Run the interactive project generator:

```bash
ccpf
```

The CLI asks for the project name, description, Python version, Prefect version,
Docker image name, and Docker image tag. The image name defaults to the
generated project slug and the tag defaults to `latest`. Python and Prefect
defaults are pinned in `ccpf/template/cookiecutter.json`.

Options can be supplied directly:

```bash
ccpf \
  --project-name "My Prefect Project" \
  --description "A reusable workflow project" \
  --python-version 3.12 \
  --prefect-version 3.8.4 \
  --image-name my-prefect-image \
  --tag latest \
  --output-dir .
```

Use `ccpf --help` to see all available options. The same
command is available as a Python module:

```bash
python -m ccpf
```

## Deployment Modes

The generator defaults to `centralized`, which creates an application
deployment helper for an existing Prefect server and Docker work pool. Use
`--deployment-mode` to choose a different artifact set:

| Mode | Generated deployment files | Server ownership |
| --- | --- | --- |
| `none` | `prefect.yaml` only | Existing server and worker |
| `centralized` | `Dockerfile`, `Makefile`, `docker-compose.yml` | Existing server and work pool |
| `centralized` with `--include-centralized-server-compose` | The centralized files plus `docker-compose.server.yml` and `Dockerfile.worker` | Generated optional server stack |
| `standalone` | `Dockerfile`, `Dockerfile.worker`, `Makefile`, one combined `docker-compose.yml` | Generated server, database, and worker |

Every mode accepts `--prefect-server-url`, including its port. The default is
`http://127.0.0.1:4200/api`; the port is validated and propagated to generated
Compose health checks, worker settings, Makefile commands, and README guidance.
The Prefect work pool remains an external resource and is never modeled as a
Compose service.

Centralized Docker output assumes the Prefect server container is named
`prefect-server` and shares `prefect-server-network` on the same Docker daemon.
The optional server Compose creates that network and runs one project-agnostic
worker named `central-docker-worker` for the shared `local-docker-pool`. Its
`Dockerfile.worker` must move with `docker-compose.server.yml` when the server
bundle is relocated. Project-specific dependencies stay in each application
image. For a remote or non-Docker server, adjust the generated container API
URL and Prefect deployment network settings as documented in the generated
README.

Generated server ports bind to `127.0.0.1`. Before exposing Prefect on another
interface, configure authentication, TLS through a reverse proxy, and secure
credentials. See [Prefect's security guidance](https://docs.prefect.io/v3/advanced/security-settings).
Generated Compose commands load `./.env`; copy `.env.example` to `.env` and
replace its database password before starting Prefect infrastructure.

For local development of the CLI itself, install the cloned repository in
editable mode instead:

```bash
uv tool install --editable .
```

Cookiecutter can also be invoked directly against the template in the cloned
repository:

```bash
uv run cookiecutter ccpf/template
```

## Generated Project

The generated project contains this general layout:

```text
project-slug/
├── prefect.yaml
├── src/
│   ├── logic/
│   ├── schemas/
│   └── workflows/
│       ├── common/
│       ├── tasks/
│       └── flows/
└── tests/
    ├── common/
    ├── data/
    │   ├── regression/
    │   └── validation/
    ├── integration/
    ├── logic/
    ├── prefect/
    └── schemas/
```

The generated source files contain only short, generic examples. They do not
contain project-specific storage, schemas, model implementations, events, or
business logic.

## Prefect Configuration

The generated `prefect.yaml` includes a runnable example deployment whose code
is baked into a Docker image. The Docker image name and tag come from the CLI
inputs. The default colocated worker uses the locally built image without a
registry push or runtime Git clone.

The file also includes a fully commented event-triggered deployment example.
It is documentation only: no automation is registered and no event is
emitted. Uncomment and adapt it only after the project has a real event
producer and a deployment that should react to it.

The `build_image` and event payload expressions in `prefect.yaml` are resolved
by Prefect during deployment. They are intentionally preserved through the
earlier Cookiecutter rendering step.

## Running the Generated Project

After generating a project:

```bash
cd project-slug
uv sync --extra dev
uv run python -m src.workflows.flows.example_flow
```

Replace the example flow and task, then configure a deployment in
`prefect.yaml` or create one through the Prefect CLI.

## Running A Local Prefect Server

If Prefect is not already running, start this ephemeral development server in
a separate terminal:

For persistent development or shared environments, the recommended setup is a
Docker Compose deployment with PostgreSQL as the Prefect database. The command
below is only a quick local example and intentionally does not provide
persistent storage.

```bash
docker run --rm --name prefect-server \
  -p 4200:4200 \
  prefecthq/prefect:3.8.4-python3.12 \
  prefect server start --host 0.0.0.0 --port 4200
```

This example does not persist data. Server state, deployments, and flow-run
history are lost when the container stops or is removed. Use it only for local
development and testing. The Prefect UI is available at
`http://127.0.0.1:4200`, and the API is available at
`http://127.0.0.1:4200/api`.

In another terminal, configure the CLI and worker to use this server:

```bash
export PREFECT_API_URL=http://127.0.0.1:4200/api
```

## Deploying a Worker

The Docker configuration expects the shared `local-docker-pool` Docker work
pool and a worker running
on a host with access to a Docker daemon. Configure the Prefect API or log in
to Prefect Cloud before using these commands.

```bash
uv run prefect work-pool create --type docker local-docker-pool

uv run prefect deploy src/workflows/flows/example_flow.py:example_flow \
  --name example-flow \
  --pool local-docker-pool

uv run prefect worker start --pool local-docker-pool --type docker
```

The shared work pool name must match the value in `prefect.yaml` and the pool
used by `prefect deploy`. A single central Docker worker can execute
deployments from multiple projects; each deployment supplies its own image and
dependencies. Run the worker as a long-running process or service in the
environment where flow runs should execute. The generated deployment builds
the image locally and does not push it. For a remote worker, add a Prefect
Docker push step, configure registry credentials, and use an appropriate image
pull policy.

## Development

Install the development dependencies before running the repository checks:

```bash
uv sync --extra dev
```

Run the template tests and checks with:

```bash
uv run pytest
uv run ruff check .
```

The tests render a temporary project, validate its YAML, execute the example
flow, and verify that the packaged template can be used by the CLI.
