FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

WORKDIR /app

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --uid 10001 appuser \
    && mkdir -p /data /app/staticfiles \
    && chown -R appuser:appgroup /data /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY --chown=appuser:appgroup . .
RUN chmod +x /app/entrypoint.sh
RUN DJANGO_SECRET_KEY=build-only-secret-key-not-used-at-runtime \
    python manage.py collectstatic --noinput

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/consult/health/', timeout=3)"

ENTRYPOINT ["/app/entrypoint.sh"]
