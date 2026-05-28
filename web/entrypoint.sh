#!/bin/sh
set -e

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting gunicorn..."
exec gunicorn pinn_web.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 4 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
