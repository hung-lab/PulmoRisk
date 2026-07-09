FROM python:3.10

# ENV DEBIAN_FRONTEND=noninteractive
# Fix: uv defaults to hardlinks for cache efficiency, but fails when the cache
# and target are on different filesystems (common in Docker). Setting copy mode
# suppresses the warning and ensures installs always succeed.
ENV UV_LINK_MODE=copy

# Step 1: system packages
RUN apt-get update && apt-get install -y \
  cmake \
  python3-tk \
  tk-dev \
  build-essential \
  git \
  curl \
  libgl1 \
  libglib2.0-0 \
  r-base \
  r-base-dev \
  libcurl4-openssl-dev \
  libuv1-dev \
  libssl-dev \
  libxml2-dev \
  libpng-dev \
  libicu-dev \
  xz-utils \
  rustc \
  cargo \
  && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY scripts/ ./scripts/


RUN uv sync --reinstall

RUN uv run python -c "import app; print('APP OK:', app.__file__)"

# Verify R packages installed correctly
RUN Rscript -e "cat(R.version\$major, R.version\$minor, '\n')"

RUN useradd --create-home --shell /bin/bash appuser \
  && mkdir -p /app/build /app/dist \
  && chown -R appuser:appuser /app


USER appuser


ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV TMPDIR=/tmp
ENV R_LIBS_USER=/home/appuser/R/library
ENV R_LIBS=/home/appuser/R/library

ENTRYPOINT ["uv", "run", "pulmorisk"]
