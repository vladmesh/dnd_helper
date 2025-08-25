FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.7.1

COPY api/pyproject.toml /app/pyproject.toml
RUN poetry install --no-interaction --no-ansi --no-root

# Copy API source
COPY api/src /app/src
# Copy shared models into API source path for imports
COPY shared_models/src/shared_models /app/src/shared_models

EXPOSE 8000


