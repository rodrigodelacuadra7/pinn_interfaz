#!/bin/sh
set -e

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Applying database migrations..."
python manage.py migrate --noinput

echo "==> Seeding initial PINN model (idempotent)..."
python manage.py seed_modelo

# Crea el superusuario automáticamente si se pasan las variables de entorno.
# Idempotente: falla silenciosamente si el usuario ya existe.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "==> Asegurando superusuario '${DJANGO_SUPERUSER_USERNAME}'..."
  python manage.py createsuperuser --noinput || true
fi

echo "==> Starting gunicorn on port ${PORT:-7860}..."
exec gunicorn pinn_web.wsgi:application \
  --bind "0.0.0.0:${PORT:-7860}" \
  --workers 2 \
  --threads 4 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
