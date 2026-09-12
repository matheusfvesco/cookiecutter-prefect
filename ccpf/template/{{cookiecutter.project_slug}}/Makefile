PREFECT_API_URL ?= {{ cookiecutter.prefect_server_url }}
PREFECT_CONTAINER_API_URL ?= http://prefect-server:{{ cookiecutter.prefect_server_port }}/api
PREFECT_PORT ?= {{ cookiecutter.prefect_server_port }}
WORK_POOL ?= {{ cookiecutter.work_pool_name }}

.PHONY: deploy create-pool{% if cookiecutter.deployment_mode == "standalone" %} up down{% elif cookiecutter.deployment_mode == "centralized" and cookiecutter.include_centralized_server_compose %} server-up server-down{% endif %}

deploy:
	{% if cookiecutter.deployment_mode == "standalone" %}docker compose run --rm deploy{% else %}PREFECT_CONTAINER_API_URL=$(PREFECT_CONTAINER_API_URL) docker compose run --rm deploy{% endif %}

create-pool:
	@PREFECT_API_URL=$(PREFECT_API_URL) uv run prefect work-pool inspect $(WORK_POOL) >/dev/null 2>&1 || \
		PREFECT_API_URL=$(PREFECT_API_URL) uv run prefect work-pool create --type docker $(WORK_POOL)
{% if cookiecutter.deployment_mode == "standalone" %}
up:
	docker compose up -d prefect-server postgres prefect-worker

down:
	docker compose down
{% elif cookiecutter.deployment_mode == "centralized" and cookiecutter.include_centralized_server_compose %}
server-up:
	docker compose -f docker-compose.server.yml up -d

server-down:
	docker compose -f docker-compose.server.yml down
{% endif %}
