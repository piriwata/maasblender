FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/base_simulators/walking

COPY libs/mblib /workspace/libs/mblib
COPY src/base_simulators/walking/pyproject.toml ./
COPY src/base_simulators/walking/uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/base_simulators/walking ./

ENV PATH="/workspace/src/base_simulators/walking/.venv/bin:$PATH"

RUN chown -R nobody:nogroup .
USER nobody

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
