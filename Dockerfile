# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11.4
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /teamsa-app

# Crear usuario no-root
RUN adduser \
    --disabled-password \
    --gecos "" \
    --uid 10001 \
    teamsauser

# Instalar dependencias del sistema para WeasyPrint (generación de PDF)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python con caché
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install --no-cache-dir -r requirements.txt

# Copy the source code into the container.
COPY ./app ./app
COPY ./web ./web
COPY ./alembic.ini ./alembic.ini
COPY ./db_migraciones ./db_migraciones

# Switch to the non-root user
USER teamsauser

# Expose the port that the application listens on.
EXPOSE 8001

# Run the application.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
