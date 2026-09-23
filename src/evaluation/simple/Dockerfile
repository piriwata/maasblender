FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/evaluation/simple
COPY libs/mblib /workspace/libs/mblib
COPY src/evaluation/simple/pyproject.toml src/evaluation/simple/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY src/evaluation/simple ./

USER nobody

ENTRYPOINT ["uv", "run", "--no-sync", "uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
