FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/scenario/commuter

COPY libs/mblib /workspace/libs/mblib
COPY src/scenario/commuter/pyproject.toml ./
COPY src/scenario/commuter/uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/scenario/commuter ./

ENV PATH="/workspace/src/scenario/commuter/.venv/bin:$PATH"

RUN chown -R nobody:nogroup .
USER nobody

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
