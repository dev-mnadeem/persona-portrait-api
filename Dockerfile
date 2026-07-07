# --- build stage: resolve dependencies into a self-contained virtualenv ------
FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# --- runtime stage -----------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=ai_Influencer.settings

COPY --from=builder /opt/venv /opt/venv

RUN useradd --create-home --uid 10001 portrait
WORKDIR /app

COPY --chown=portrait:portrait . /app

# Writable state lives outside the source tree so it can be a volume.
RUN mkdir -p /data/media /data/static && chown -R portrait:portrait /data

USER portrait

ENV DJANGO_DB_PATH=/data/db.sqlite3 \
    DJANGO_MEDIA_ROOT=/data/media

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "ai_Influencer.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
