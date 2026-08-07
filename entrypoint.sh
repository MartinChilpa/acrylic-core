#!/bin/bash
set -e

echo "Running database migrations..."
python manage.py migrate --settings=acrylic.settings

echo "Collecting static files..."
python manage.py collectstatic --noinput --settings=acrylic.settings

echo "Starting Gunicorn..."
exec gunicorn acrylic.wsgi --bind 0.0.0.0:8000 --workers 4
