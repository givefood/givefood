# syntax=docker/dockerfile:1.7

# Tracks the latest 3.12 patch release, matching requires-python in
# pyproject.toml. Picks up base image security updates on rebuild.
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.10.10 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies resolve in their own layer, so a source-only change reuses it.
# The cache mount means even a lockfile change installs from local wheels.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

EXPOSE 8000

# gunicorn.conf.py supplies workers and timeout. If the Coolify start command
# currently runs migrations first, keep doing that there rather than here, so
# it happens once per deploy instead of once per container.
CMD ["gunicorn", "givefood.wsgi:application", "-c", "gunicorn.conf.py", "-b", "0.0.0.0:8000"]
