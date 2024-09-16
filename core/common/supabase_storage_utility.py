import requests
import os
import io
import logging
from PIL import Image
from supabase import create_client
logger = logging.getLogger(__name__)
from .supabase_client import supabase
import io
import logging

logger = logging.getLogger(__name__)



import io
import logging
import requests

from django.conf import settings

logger = logging.getLogger(__name__)

class SupabaseStorageUtility:
    def __init__(self):
        self.supabase = supabase
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_SERVICE_ROLE_KEY

    def upload_file(self, bucket_name, file_name, file_content, is_image=False):
        try:
            if isinstance(file_content, io.BytesIO):
                file_content = file_content.getvalue()
            elif not isinstance(file_content, bytes):
                file_content = bytes(file_content)

            headers = {
                "Authorization": f"Bearer {self.key}",
                "apikey": self.key,
            }

            url = f"{self.url}/storage/v1/object/{bucket_name}/{file_name}"

            response = requests.post(
                url,
                headers=headers,
                files={"file": (file_name, file_content, "image/jpeg" if is_image else "application/octet-stream")}
            )

            if response.status_code == 200:
                public_url = f"{self.url}/storage/v1/object/public/{bucket_name}/{file_name}"
                logger.info(f"Successfully uploaded {file_name} to Supabase")
                return public_url
            else:
                logger.error(f"Failed to upload {file_name} to Supabase. Status code: {response.status_code}, Response: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error uploading {file_name} to Supabase: {str(e)}")
            return None