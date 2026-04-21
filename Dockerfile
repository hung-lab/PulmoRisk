# Use Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  tk \
  python3-tk \
  python3-dev \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

# Copy uv and install it
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml README.md uv.lock ./
COPY src/ ./src/
COPY scripts/ ./scripts/

# Install dependencies
RUN uv sync --locked --all-extras

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser \
  && chown -R appuser:appuser /app

USER appuser

# Set entrypoint
ENTRYPOINT ["uv", "run", "python", "-m", "app.main"]

