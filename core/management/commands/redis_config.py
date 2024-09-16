from django.core.management.base import BaseCommand
from django.apps import apps
from core.models import RedisConfig
import json

class Command(BaseCommand):
    help = 'Generates and stores a JSON configuration for Redis key initialization based on model relationships'

    def handle(self, *args, **options):
        config = {
            "redis_initialization": []
        }

        # Get all models from all installed apps
        for model in apps.get_models():
            # Example: Assume we initialize Redis keys for all ForeignKey relationships
            for field in model._meta.fields:
                if field.get_internal_type() == 'ForeignKey':
                    related_model = field.related_model
                    key_name = f"user:{{user_id}}:{related_model.__name__.lower()}s"
                    config["redis_initialization"].append({
                        "key": key_name,
                        "initial_value": []
                    })

        # Save or update the configuration in the database
        config_name = 'default_redis_config'
        obj, created = RedisConfig.objects.update_or_create(
            name=config_name,
            defaults={'data': config}
        )

        self.stdout.write(self.style.SUCCESS('Successfully stored Redis configuration in the database.'))