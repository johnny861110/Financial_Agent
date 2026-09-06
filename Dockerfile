# --- Stage 1: Builder ---
FROM python:3.10-slim AS builder

# uv is copied from its published image rather than fetched by the install
# script. The script downloads a GitHub release asset, which this build network
# resets (curl: (56) Recv failure: Connection reset by peer); the registry is
# reachable when raw release downloads are not. Pinned to the version that
# produced uv.lock so --frozen stays honest.
COPY --from=ghcr.io/astral-sh/uv:0.9.10 /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# This build network runs at roughly 270 KB/s. Downloading in parallel starved
# the smaller wheels -- streamlit's 9.7MB had not arrived after 325s while
# pyarrow's 40.8MB shared the link -- so downloads are serialized: each one then
# gets the whole pipe and finishes well inside the timeout.
ENV UV_HTTP_TIMEOUT=300 \
    UV_CONCURRENT_DOWNLOADS=1

# Only the dependency manifests, so editing application code does not
# invalidate the expensive resolve-and-install layer below.
COPY pyproject.toml uv.lock README.md ./

# This link drops connections mid-transfer at random (observed: a wheel read
# stopping after 1.1MB of 8MB, and "Recv failure: Connection reset by peer"),
# so a single attempt is a coin flip. Each retry resumes from the cache mount
# rather than refetching ~300MB, so attempts accumulate progress. The final
# unguarded sync makes the layer fail honestly if every attempt failed.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    for attempt in 1 2 3 4 5 6; do \
        uv sync --frozen --no-dev && break; \
        echo "uv sync attempt ${attempt} failed, retrying"; \
        sleep 5; \
    done; \
    uv sync --frozen --no-dev

# --- Stage 2: Runtime ---
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Created before the copies so each COPY can set ownership directly. A trailing
# `RUN chown -R appuser /app` would instead write a new layer containing another
# full copy of the virtualenv, and would re-run whenever any source file changed.
RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser convert_financial_report.py ./
COPY --chown=appuser:appuser data/ ./data/

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
