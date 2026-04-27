FROM python:3.10

# ENV DEBIAN_FRONTEND=noninteractive
# Fix: uv defaults to hardlinks for cache efficiency, but fails when the cache
# and target are on different filesystems (common in Docker). Setting copy mode
# suppresses the warning and ensures installs always succeed.
ENV UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y \
  python3-tk \
  tk-dev \
  build-essential \
  git \
  curl \
  && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY scripts/ ./scripts/

RUN uv sync --reinstall

RUN uv run python -c "import app; print('APP OK:', app.__file__)"

RUN useradd --create-home --shell /bin/bash appuser \
  && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["uv run tkinter-app"]
