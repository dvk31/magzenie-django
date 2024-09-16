import base64
from pathlib import Path
from django.core.management.base import BaseCommand
from decouple import Config, RepositoryEnv

class Command(BaseCommand):
    help = 'Generate Kubernetes ConfigMap and Secret from .env file'

    def handle(self, *args, **kwargs):
        env_path = Path('.') / '.env'
        config = Config(RepositoryEnv(env_path))

        # Separate non-sensitive and sensitive data
        config_map_data = {}
        secret_data = {}

        sensitive_keys = {
            'SECRET_KEY', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 
            'POSTGRES_HOST', 'POSTGRES_PORT', 'SUPABASE_API_KEY', 'SUPABASE_SERVICE_ROLE_KEY',
            'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'SENDGRID_API_KEY', 
            'MAILGUN_API_KEY', 'MAILGUN_DOMAIN', 'OPENAI_API_KEY', 'CELERY_BROKER_URL', 
            'CELERY_RESULT_BACKEND', 'REDIS_PASSWORD'
        }

        # Read .env file directly
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                if key in sensitive_keys:
                    secret_data[key] = base64.b64encode(value.encode()).decode()
                else:
                    config_map_data[key] = value

        # Create ConfigMap YAML
        config_map_yaml = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: gateway-config
data:
"""
        for key, value in config_map_data.items():
            config_map_yaml += f"  {key}: \"{value}\"\n"

        # Create Secret YAML
        secret_yaml = f"""
apiVersion: v1
kind: Secret
metadata:
  name: gateway-secret
type: Opaque
data:
"""
        for key, value in secret_data.items():
            secret_yaml += f"  {key}: \"{value}\"\n"

        # Save to files
        with open('configmap.yaml', 'w') as config_map_file:
            config_map_file.write(config_map_yaml)

        with open('secret.yaml', 'w') as secret_file:
            secret_file.write(secret_yaml)

        self.stdout.write(self.style.SUCCESS('Successfully generated configmap.yaml and secret.yaml'))
