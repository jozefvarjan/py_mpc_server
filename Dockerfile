# syntax=docker/dockerfile:1

########################
# Builder stage
########################
FROM python:3.14-slim AS builder

# uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# uv build-time tuning:
#  - compile bytecode for faster cold starts
#  - copy (not link) packages so they live inside the image layer
#  - install into a project-local .venv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first, using the lockfile, for maximum layer caching.
# The source is intentionally NOT copied yet so this layer is only rebuilt
# when pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy the application source and install the project itself.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

########################
# Runtime stage
########################
FROM python:3.14-slim AS runtime

# Keep Python lean and predictable in containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Run as an unprivileged user
RUN useradd --create-home --uid 10001 appuser

# Bring over the fully-built virtualenv and the app source
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser

# Render injects PORT at runtime; the app reads it (defaults to 8080 locally).
ENV PORT=8080
EXPOSE 8080

# The venv is on PATH, so run the interpreter directly (no uv needed at runtime).
CMD ["python", "main.py"]
