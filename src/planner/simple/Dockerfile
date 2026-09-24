FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/planner/simple

COPY libs/mblib /workspace/libs/mblib
COPY src/planner/simple/pyproject.toml ./
COPY src/planner/simple/uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/planner/simple ./

ENV PATH="/workspace/src/planner/simple/.venv/bin:$PATH"

RUN chown -R nobody:nogroup .
USER nobody

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
