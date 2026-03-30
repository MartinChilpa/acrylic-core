release: python manage.py migrate
web: gunicorn acrylic.wsgi
worker: celery -A acrylic worker --loglevel=info --concurrency=1
