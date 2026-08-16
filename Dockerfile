# Multi-stage build for jobot — headless runtime image.
#
# Stage 1: build the wheel (isolated from runtime).
# Stage 2: slim runtime with Python, LaTeX/poppler optional (fallback engine used otherwise).

FROM python:3.12-slim AS builder
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip setuptools wheel \
    && python -m pip install build \
    && python -m build --wheel

FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.source="https://github.com/aryansinghnagar/JoBot" \
      org.opencontainers.image.description="Autonomous Job Application Operating System (jobot)" \
      org.opencontainers.image.licenses="AGPL-3.0"

ENV PYTHONUNBUFFERED=1 \
    JOBOT_CONTAINER=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist/*.whl /tmp/jobot.whl
RUN pip install --no-cache-dir /tmp/jobot.whl && rm /tmp/jobot.whl

RUN useradd --create-home --uid 1000 jobot
USER jobot
WORKDIR /home/jobot
VOLUME ["/home/jobot/.jobot"]

ENTRYPOINT ["jobot"]
CMD ["--help"]