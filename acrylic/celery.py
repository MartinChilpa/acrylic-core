import os
from celery import Celery
from decouple import config
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acrylic.settings')

app = Celery('acrylic')

# Lógica para detectar si estamos en local o en la nube
# Heroku Redis usually provides REDIS_URL. Older configs may use REDISCLOUD_URL.
# If neither is set (local dev), default to localhost.
REDIS_URL = config('REDIS_URL', default=config('REDISCLOUD_URL', default='redis://localhost:6379/0'))

app.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,

    # Reduce the number of Redis connections to avoid "max number of clients reached"
    # (common with RedisCloud + multiple worker processes).
    broker_pool_limit=config('CELERY_BROKER_POOL_LIMIT', default=1, cast=int),
    redis_max_connections=config('CELERY_REDIS_MAX_CONNECTIONS', default=5, cast=int),
    
    # IMPORTANTE: Si usas una cola personalizada, el worker DEBE conocerla
    task_default_queue='celery', 
    
    # Esto ayuda a que el worker no se "congele" con tareas pesadas de Chartmetric
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    broker_transport_options={
        'visibility_timeout': 3600, # 1 hora (útil para tareas largas de APIs)
        'max_connections': config('CELERY_BROKER_MAX_CONNECTIONS', default=5, cast=int),
        'socket_timeout': config('CELERY_BROKER_SOCKET_TIMEOUT', default=30, cast=int),
        'socket_connect_timeout': config('CELERY_BROKER_SOCKET_CONNECT_TIMEOUT', default=30, cast=int),
        'max_retries': 5,
    }
)

# Simplifica el autodiscover
app.autodiscover_tasks()
