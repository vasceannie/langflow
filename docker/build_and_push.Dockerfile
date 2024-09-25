# syntax=docker/dockerfile:1
# Keep this syntax directive! It's used to enable Docker BuildKit


################################
# BUILDER-BASE
# Used to build deps + create our virtual environment
################################

# 1. use python:3.12.3-slim as the base image until https://github.com/pydantic/pydantic-core/issues/1292 gets resolved
# 2. do not add --platform=$BUILDPLATFORM because the pydantic binaries must be resolved for the final architecture
# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    # deps for installing poetry
    curl \
    # deps for building python deps
    build-essential \
    # npm
    npm \
    # gcc
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=src/backend/base/README.md,target=src/backend/base/README.md \
    --mount=type=bind,source=src/backend/base/uv.lock,target=src/backend/base/uv.lock \
    --mount=type=bind,source=src/backend/base/pyproject.toml,target=src/backend/base/pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD ./src /app/src

COPY src/frontend/package.json /tmp/package.json
RUN cd /tmp && npm install \
    && rm -rf src/frontend/node_modules \
    && cp -a /tmp/node_modules /app/src/frontend \
    && cd /app/src/frontend && npm run build \
    && cp -r /app/src/frontend/build /app/src/backend/base/langflow/frontend

ADD ./pyproject.toml /app/pyproject.toml
ADD ./uv.lock /app/uv.lock

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []
################################
# RUNTIME
# Setup user, utilities and copy the virtual environment only
################################


LABEL org.opencontainers.image.title=langflow
LABEL org.opencontainers.image.authors=['Langflow']
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.url=https://github.com/langflow-ai/langflow
LABEL org.opencontainers.image.source=https://github.com/langflow-ai/langflow


ENV LANGFLOW_HOST=0.0.0.0
ENV LANGFLOW_PORT=7860

CMD ["langflow", "run"]
