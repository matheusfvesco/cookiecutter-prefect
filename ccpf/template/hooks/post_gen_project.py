import json
from pathlib import Path


project_directory = Path.cwd()
context_path = project_directory / ".ccpf-deployment-context.json"
context = json.loads(context_path.read_text(encoding="utf-8"))
context_path.unlink()

mode = context["deployment_mode"]
files = {
    ".dockerignore",
    "Dockerfile",
    "Dockerfile.worker",
    "Makefile",
    "docker-compose.yml",
    "docker-compose.server.yml",
}

if mode == "none":
    files_to_remove = files
elif mode == "centralized" and context["include_centralized_server_compose"]:
    files_to_remove = set()
elif mode == "centralized":
    files_to_remove = {"Dockerfile.worker", "docker-compose.server.yml"}
else:
    files_to_remove = {"docker-compose.server.yml"}

for filename in files_to_remove:
    path = project_directory / filename
    if path.exists():
        path.unlink()
