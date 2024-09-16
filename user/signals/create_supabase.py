import os
import logging
import json
import subprocess
import time
from django.db.models.signals import post_save
from django.dispatch import receiver
from celery import shared_task
from urllib.parse import urlparse
from django.conf import settings
from django.db import transaction
from user.models import UsersModel, SupabaseInstance
import requests
from celery.exceptions import MaxRetriesExceededError
import tempfile

logger = logging.getLogger(__name__)

@receiver(post_save, sender=UsersModel)
def create_supabase_instance(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New user created with ID: {instance.id}. Scheduling Supabase instance creation.")
        transaction.on_commit(lambda: create_supabase_instance_task.delay(instance.id))

def wait_for_supabase_ready(url, timeout=300):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/rest/v1/")
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(10)
    return False

def deploy_supabase_instance(user_id):
    logger.info(f"Starting deployment of Supabase instance for user {user_id}")
    app_name = f"supabase-{user_id}"
    
    # Extract domain from CAPROVER_URL
    caprover_domain = urlparse(settings.CAPROVER_URL).netloc.split(':')[0]
    
    # Generate secure random values for environment variables
    postgres_password = os.urandom(24).hex()
    jwt_secret = os.urandom(32).hex()
    anon_key = os.urandom(32).hex()
    service_role_key = os.urandom(32).hex()

    try:
        # Authenticate with CapRover
        auth_url = f"{settings.CAPROVER_URL}/api/v2/login"
        auth_data = {"password": settings.CAPROVER_PASSWORD}
        auth_response = requests.post(auth_url, json=auth_data)
        auth_response.raise_for_status()
        token = auth_response.json()['data']['token']

        headers = {
            'x-captain-auth': token,
            'Content-Type': 'application/json'
        }

        # Deploy Supabase app
        deploy_url = f"{settings.CAPROVER_URL}/api/v2/user/apps/appDefinitions/register"
        deploy_data = {
            "appName": app_name,
            "hasPersistentData": True,
            "containerHttpPort": "8000",
            "envVars": [
                {"key": "POSTGRES_PASSWORD", "value": postgres_password},
                {"key": "JWT_SECRET", "value": jwt_secret},
                {"key": "ANON_KEY", "value": anon_key},
                {"key": "SERVICE_ROLE_KEY", "value": service_role_key},
                {"key": "SITE_URL", "value": f"https://{app_name}.{caprover_domain}"},
                {"key": "DASHBOARD_USERNAME", "value": "admin"},
                {"key": "DASHBOARD_PASSWORD", "value": os.urandom(16).hex()},
                # Add other necessary environment variables here
            ],
            "volumes": [
                {
                    "volumeName": f"{app_name}-db-data",
                    "containerPath": "/var/lib/postgresql/data"
                },
                {
                    "volumeName": f"{app_name}-storage",
                    "containerPath": "/storage"
                }
            ],
            "ports": [
                {
                    "containerPort": 5432,
                    "hostPort": 5432
                }
            ],
            "notExposeAsWebApp": False,
            "forceSsl": True,
            "captainDefinitionContent": {
                "schemaVersion": 2,
                "dockerfileLines": [
                    "FROM supabase/supabase:latest",
                    "EXPOSE 8000",
                    "CMD [\"/usr/local/bin/supabase\", \"start\"]"
                ]
            }
        }

        deploy_response = requests.post(deploy_url, headers=headers, json=deploy_data)
        deploy_response.raise_for_status()
        
        logger.info(f"Supabase app deployed successfully for user {user_id}")

        # Get the app URL
        app_url = f"https://{app_name}.{caprover_domain}"

        # Wait for Supabase to be ready
        if not wait_for_supabase_ready(app_url):
            raise Exception("Supabase instance failed to initialize within the expected time")

        logger.info(f"Supabase instance is ready at {app_url}")

        return {
            "project_ref": app_name,
            "project_id": app_name,
            "db_password": postgres_password,
            "instance_url": app_url,
            "api_key": service_role_key,
            "anon_key": anon_key
        }

    except requests.RequestException as e:
        logger.error(f"Error deploying Supabase instance: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Response content: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error deploying Supabase instance: {str(e)}")
        raise

@shared_task(bind=True, max_retries=1)
def create_supabase_instance_task(self, user_id):
    logger.info(f"Starting create_supabase_instance_task for user {user_id}")
    try:
        user = UsersModel.objects.get(id=user_id)
        logger.info(f"User {user.username} retrieved from database")
        
        # Deploy Supabase instance using CapRover CLI
        instance_data = deploy_supabase_instance(str(user_id))
        logger.info(f"Supabase instance deployed for user {user.username}")

        # Create SupabaseInstance object
        supabase_instance = SupabaseInstance.objects.create(
            user=user,
            project_ref=instance_data['project_ref'],
            project_id=instance_data['project_id'],
            db_password=instance_data['db_password'],
            instance_url=instance_data['instance_url'],
            api_key=instance_data['api_key'],
            anon_key=instance_data['anon_key']
        )
        logger.info(f"SupabaseInstance object created for user {user.username}")

        logger.info(f"Supabase instance creation completed for user {user.username}")
        return f"Supabase instance created successfully for user {user.username}"

    except UsersModel.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error creating Supabase instance for user {user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)