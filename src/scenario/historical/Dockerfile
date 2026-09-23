FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/scenario/historical

COPY libs/mblib /workspace/libs/mblib
COPY src/scenario/historical/pyproject.toml ./
COPY src/scenario/historical/uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/scenario/historical ./

ENV PATH="/workspace/src/scenario/historical/.venv/bin:$PATH"

RUN chown -R nobody:nogroup .
USER nobody

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
