FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/simulation_broker

COPY libs/mblib /workspace/libs/mblib
COPY src/simulation_broker/pyproject.toml ./
COPY src/simulation_broker/uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/simulation_broker ./

ENV PATH="/workspace/src/simulation_broker/.venv/bin:$PATH"

RUN chown -R nobody:nogroup .
USER nobody

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
