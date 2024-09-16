import logging
import traceback
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.management import call_command
from django.db import transaction
from user.models import DynamicModel

logger = logging.getLogger(__name__)

@receiver(post_save, sender=DynamicModel)
def handle_dynamic_model_save(sender, instance, created, **kwargs):
    try:
        with transaction.atomic():
            if created:
                logger.info(f"Creating new Supabase table for DynamicModel id: {instance.id}")
                call_command('update_supabase_table', 'create', instance.id)
            else:
                logger.info(f"Updating Supabase table for DynamicModel id: {instance.id}")
                call_command('update_supabase_table', 'update', instance.id)
    except Exception as e:
        logger.error(f"Error in handle_dynamic_model_save for DynamicModel id: {instance.id}")
        logger.error(traceback.format_exc())
        raise

@receiver(post_delete, sender=DynamicModel)
def handle_dynamic_model_delete(sender, instance, **kwargs):
    try:
        with transaction.atomic():
            logger.info(f"Deleting Supabase table for DynamicModel id: {instance.id}")
            call_command('update_supabase_table', 'delete', instance.id)
    except Exception as e:
        logger.error(f"Error in handle_dynamic_model_delete for DynamicModel id: {instance.id}")
        logger.error(traceback.format_exc())
        raise