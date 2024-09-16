import os
import logging
import requests
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
from django.core.files.storage import default_storage
from hellogpt.gssettings import PublicGoogleCloudStorage

logger = logging.getLogger(__name__)

class ImageUploader:
    @staticmethod
    def fetch_image(image_url):
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except requests.exceptions.RequestException as e:
            logger.error(f"Error occurred while fetching the image: {e}")
            raise
        except IOError as e:
            logger.error(f"Error occurred while opening the image: {e}")
            raise

    @staticmethod
    def generate_filename(model_instance, field_name):
        return f"{model_instance._meta.model_name}_{model_instance.id}_{field_name}.png"

  
    def save_image(model_instance, field_name, image):
        try:
            filename = ImageUploader.generate_filename(model_instance, field_name)
            
            # Saving the image data in the ContentFile object
            image_data = BytesIO()
            image.save(image_data, format='PNG')
            image_data.seek(0)
            content_file = ContentFile(image_data.read())

            # Save the image to the default storage
            file_name = default_storage.save(filename, content_file)

            # After the file is saved, generate the URL
            file_url = default_storage.url(file_name)

            # Update the model instance's field with the new file's URL
            setattr(model_instance, field_name, file_url)
            model_instance.save(update_fields=[field_name])

            logger.info(f"Image uploaded successfully for {model_instance._meta.model_name} instance with ID {model_instance.id}")
            return file_url  # This will return the public URL of the file if the bucket is public.
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving the image to Google Cloud Storage: {e}")
            raise


    @staticmethod
    def upload_image_from_url(model_instance, field_name, image_url):
        try:
            # Fetch the image using the provided URL
            image = ImageUploader.fetch_image(image_url)
            ImageUploader.save_image(model_instance, field_name, image)
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            raise