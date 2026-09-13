FROM prefecthq/prefect:{{ cookiecutter.prefect_version }}-python{{ cookiecutter.python_version.split('.')[0] }}.{{ cookiecutter.python_version.split('.')[1] }}

WORKDIR /opt/{{ cookiecutter.project_slug }}
COPY . .
RUN uv sync --no-dev

ENV PATH="/opt/{{ cookiecutter.project_slug }}/.venv/bin:$PATH"
