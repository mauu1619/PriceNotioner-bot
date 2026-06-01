# Stage 1: Builder
FROM python:3.12-slim AS builder

# Retrieve the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Copy dependency manifests
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
# --no-dev ensures development dependencies are excluded
# --no-install-project avoids installing the current source project itself
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Final minimal image
FROM python:3.12-slim

# Create a non-root user and group for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Prevent Python from writing pyc files, set unbuffered mode, and add venv to PATH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy the pre-built virtual environment from the builder stage, setting ownership
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy the application code, setting ownership
COPY --chown=appuser:appuser . .

# Create logs directory and set ownership
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

# Switch to the non-root user
USER appuser

# Default command
CMD ["python", "-m", "src.main"]
