import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "monitor_site.settings")
app = Celery("monitor_site")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
