release: python manage.py migrate
web: gunicorn acrylic.wsgi
worker: celery --app=acrylic worker --concurrency=2
