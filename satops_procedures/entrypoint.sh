#!/bin/bash
set -e

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && \
   [ -n "$DJANGO_SUPERUSER_EMAIL" ] && \
   [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "==> Creating superuser (if not exists)..."
    python manage.py createsuperuser --noinput 2>/dev/null || true
fi

if [ "$SEED_ON_STARTUP" = "true" ]; then
    echo "==> Seeding database..."
    python manage.py seed_all
fi

echo "==> Starting Gunicorn on :8000..."
exec gunicorn satops.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
