import os
from celery import Celery
from decouple import config


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acrylic.settings')

app = Celery('acrylic')
#app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.update(
    BROKER_URL=config('REDISCLOUD_URL', ''),
    CELERY_RESULT_BACKEND=config('REDISCLOUD_URL', ''),
    #CELERY_ALWAYS_EAGER=True,
    BROKER_TRANSPORT_OPTIONS={
        'max_retries': 5,
        'max_connections': 30,
    }
)

app.autodiscover_tasks()
