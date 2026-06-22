#!/bin/sh
set -e

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Applying database migrations..."
python manage.py migrate --noinput

echo "==> Seeding initial PINN model (idempotent)..."
python manage.py seed_modelo

echo "==> Starting gunicorn..."
# Para crear el superusuario la primera vez:
#   docker compose exec pinn-web python manage.py createsuperuser
exec gunicorn pinn_web.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 4 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
