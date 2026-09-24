FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

WORKDIR /workspace/src/user_model/favorite

COPY libs/mblib /workspace/libs/mblib
COPY src/user_model/favorite/pyproject.toml ./
COPY src/user_model/favorite/uv.lock ./

RUN uv sync --frozen --no-install-project

COPY src/user_model/favorite ./

ENV PATH="/workspace/src/user_model/favorite/.venv/bin:$PATH"

RUN chown -R nobody:nogroup .
USER nobody

ENTRYPOINT ["uvicorn", "controller:app"]
CMD ["--host", "0.0.0.0", "--port", "80"]
