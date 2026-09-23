FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/base_simulators/routedeviation
COPY libs/mblib /workspace/libs/mblib
COPY src/base_simulators/routedeviation/pyproject.toml src/base_simulators/routedeviation/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY src/base_simulators/routedeviation ./

USER nobody

ENTRYPOINT ["uv", "run", "--no-sync", "uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
