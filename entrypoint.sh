#!/bin/sh
set -e

# Run database migrations
python manage.py migrate --noinput

# Collect static files (in case STATIC_URL changed at runtime)
python manage.py collectstatic --noinput

# Create superuser from env vars (if set)
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput --email "$DJANGO_SUPERUSER_EMAIL" || true
  echo "Superuser creation attempted for $DJANGO_SUPERUSER_EMAIL"
fi

# Start the application server
exec uvicorn saleor.asgi:application \
  --host=0.0.0.0 \
  --port=${PORT:-8000} \
  --workers=2 \
  --lifespan=on \
  --ws=none \
  --no-server-header \
  --no-access-log \
  --timeout-keep-alive=35 \
  --timeout-graceful-shutdown=30 \
  --limit-max-requests=10000
