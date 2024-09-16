import json
import os
import logging
import traceback
from uuid import UUID
from datetime import datetime
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
from hellogpt.openai_storage import OpenAiStorage
from hellogpt.openai_vector_store import OpenAiVectorStore

# Configuration
DJANGO_APPS = ['user', 'agency', 'emails', 'department']
EXCLUDED_FIELDS = {
    'user': {
        'UsersModel': ['password', 'last_login']
    },
    'agency': {
        'LeadData': ['ip_address']
    },
    'department': {
        'CallRecording': ['recording_content']
    }
}

logger = logging.getLogger(__name__)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, UUID):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)
        except TypeError:
            return str(obj)

class Command(BaseCommand):
    help = 'Export data to JSON and upload to OpenAI Vector Store'

    def handle(self, *args, **kwargs):
        try:
            data = self.gather_data()
            file_path = self.create_json_file(data)
            vector_store_id = self.upload_to_vector_store(file_path)

            self.stdout.write(self.style.SUCCESS(f'Successfully exported and uploaded to OpenAI Vector Store: {vector_store_id}'))
            logger.info(f'Successfully exported and uploaded to OpenAI Vector Store: {vector_store_id}')

        except Exception as e:
            logger.error(f"Error occurred: {e}")
            logger.error(traceback.format_exc())
            self.stderr.write(self.style.ERROR(f'Error occurred: {e}'))
            self.stderr.write(self.style.ERROR(traceback.format_exc()))

    def gather_data(self):
        data = {}
        for app_name in DJANGO_APPS:
            app_config = apps.get_app_config(app_name)
            for model_name, model in app_config.models.items():
                excluded_fields = EXCLUDED_FIELDS.get(app_name, {}).get(model_name, [])
                queryset = model.objects.all()
                model_data = []
                for obj in queryset:
                    obj_data = {}
                    for field in obj._meta.fields:
                        if field.name not in excluded_fields:
                            value = getattr(obj, field.name)
                            if isinstance(value, UUID):
                                value = str(value)
                            elif isinstance(value, datetime):
                                value = value.isoformat()
                            else:
                                try:
                                    json.dumps(value)  # Check if serializable
                                except TypeError:
                                    value = str(value)  # Convert to string if not serializable
                            obj_data[field.name] = value
                    model_data.append(obj_data)

                if app_name not in data:
                    data[app_name] = {}
                data[app_name][model_name] = model_data
        return data

    def create_json_file(self, data):
        file_name = f"export_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)
        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4, cls=CustomJSONEncoder)
        logger.info(f"JSON file created at {file_path}")
        return file_path

    def upload_to_vector_store(self, file_path):
        vector_store = OpenAiVectorStore()
        storage = OpenAiStorage()

        # First, upload the file to OpenAI using OpenAiStorage
        with open(file_path, 'rb') as file:
            file_id = storage._save(file.name, file)
        
        # Then, create a vector store with the uploaded file using OpenAiVectorStore
        vector_store_response = vector_store.create_vector_store(name='Export Data', file_ids=[file_id])
        vector_store_id = vector_store_response['id']

        return vector_store_id
