FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/scenario/generator

COPY libs/mblib /workspace/libs/mblib
COPY src/scenario/generator/pyproject.toml ./
COPY src/scenario/generator/uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/scenario/generator ./

ENV PATH="/workspace/src/scenario/generator/.venv/bin:$PATH"

RUN chown -R nobody:nogroup .
USER nobody

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
