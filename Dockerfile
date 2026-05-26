FROM python:3.10

# ENV DEBIAN_FRONTEND=noninteractive
# Fix: uv defaults to hardlinks for cache efficiency, but fails when the cache
# and target are on different filesystems (common in Docker). Setting copy mode
# suppresses the warning and ensures installs always succeed.
ENV UV_LINK_MODE=copy

# Step 1: system packages
RUN apt-get update && apt-get install -y \
  python3-tk \
  tk-dev \
  build-essential \
  git \
  curl \
  libgl1 \
  libglib2.0-0 \
  r-base \
  r-base-dev \
  r-cran-jsonlite \
  r-cran-glmnet \
  libcurl4-openssl-dev \
  libssl-dev \
  libxml2-dev \
  && rm -rf /var/lib/apt/lists/*

# Step 2: CRAN packages not in debian repo
RUN Rscript -e "install.packages(c('parsnip', 'recipes', 'workflows', 'vetiver', 'bundle'), repos='https://cloud.r-project.org', Ncpus=4)"

# Step 3: verify
RUN Rscript -e "library(parsnip); library(recipes); library(workflows); library(glmnet); library(vetiver); library(jsonlite); cat('R OK\n')"

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
RUN Rscript -e "library(parsnip); library(recipes); library(workflows); library(glmnet); library(vetiver); library(jsonlite); cat('R OK\n')"

RUN useradd --create-home --shell /bin/bash appuser \
  && mkdir -p /app/build /app/dist /app/tmp \
  && chown -R appuser:appuser /app

ENV TMPDIR=/app/tmp

USER appuser

#ENTRYPOINT ["uv", "run", "tkinter-app"]
