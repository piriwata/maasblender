FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/user_model/simple
COPY libs/mblib /workspace/libs/mblib
COPY src/user_model/simple/pyproject.toml src/user_model/simple/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY src/user_model/simple ./

USER nobody

ENTRYPOINT ["uv", "run", "--no-sync", "uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
