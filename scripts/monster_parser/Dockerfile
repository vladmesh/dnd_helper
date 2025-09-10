FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps (minimal for parser scripts)
RUN pip install --no-cache-dir \
    requests==2.32.3 \
    beautifulsoup4==4.12.3 \
    pymongo==4.7.2

# Copy only the parser scripts
COPY scripts/monster_parser /app/scripts/monster_parser

# Default workdir for running scripts
WORKDIR /app/scripts/monster_parser

# No entrypoint to allow explicit command selection per run
CMD ["python3", "--version"]


