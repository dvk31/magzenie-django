import os
from celery import Celery
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellogpt.settings')

app = Celery('hellogpt')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Print out the broker URL for debugging
print(f"Celery Broker URL: {app.conf.broker_url}")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')