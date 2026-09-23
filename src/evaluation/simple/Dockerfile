FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/evaluation/simple

COPY libs/mblib /workspace/libs/mblib
COPY src/evaluation/simple/pyproject.toml ./
COPY src/evaluation/simple/uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/evaluation/simple ./

ENV PATH="/workspace/src/evaluation/simple/.venv/bin:$PATH"

RUN chown -R nobody:nogroup .
USER nobody

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
