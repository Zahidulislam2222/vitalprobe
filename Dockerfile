# syntax=docker/dockerfile:1
# VitalProbe — CLI + dashboard + demo bot in one image.
# Posture: no telemetry, no external assets; everything the container needs is baked in.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PROJECT_ENVIRONMENT=/opt/venv
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
# --no-editable so the venv is self-contained (no reference back to /app sources);
# built at /opt/venv so script shebangs match the final image path
RUN uv sync --frozen --no-dev --no-editable --extra dashboard --extra demo

FROM python:3.12-slim-bookworm
RUN useradd --create-home --uid 1000 vitalprobe
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
USER vitalprobe
WORKDIR /home/vitalprobe
# Public demo pack so the containerized prospect demo is self-contained
COPY --chown=vitalprobe:vitalprobe packs ./packs
EXPOSE 8800
CMD ["vitalprobe", "dashboard"]
