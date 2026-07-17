#!/bin/sh
set -eu

python manage.py migrate --noinput

exec gunicorn consultation_service.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 1 \
  --threads 4 \
  --timeout 30 \
  --access-logfile - \
  --error-logfile -
