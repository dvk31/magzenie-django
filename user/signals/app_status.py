import logging
import traceback
from django.db.models.signals import post_save
from django.dispatch import receiver
from user.models import App, DynamicModel, DynamicFunction, ProjectStructure

logger = logging.getLogger(__name__)

@receiver(post_save, sender=DynamicModel)
def update_dynamic_model_created(sender, instance, created, **kwargs):
    try:
        if created:
            app = instance.app
            if not app.is_dynamic_model_created:
                app.is_dynamic_model_created = True
                app.save(update_fields=['is_dynamic_model_created'])
                logger.info(f"Updated is_dynamic_model_created flag for App {app.id}")
    except Exception as e:
        logger.error(f"Error in update_dynamic_model_created: {str(e)}")
        logger.error(traceback.format_exc())

@receiver(post_save, sender=DynamicFunction)
def update_dynamic_function_created(sender, instance, created, **kwargs):
    try:
        if created and instance.app:
            app = instance.app
            if not app.is_dynamic_function_created:
                app.is_dynamic_function_created = True
                app.save(update_fields=['is_dynamic_function_created'])
                logger.info(f"Updated is_dynamic_function_created flag for App {app.id}")
    except Exception as e:
        logger.error(f"Error in update_dynamic_function_created: {str(e)}")
        logger.error(traceback.format_exc())

@receiver(post_save, sender=ProjectStructure)
def update_project_structure_created(sender, instance, created, **kwargs):
    try:
        if created:
            app = instance.app
            if not app.is_project_structure_created:
                app.is_project_structure_created = True
                app.save(update_fields=['is_project_structure_created'])
                logger.info(f"Updated is_project_structure_created flag for App {app.id}")
    except Exception as e:
        logger.error(f"Error in update_project_structure_created: {str(e)}")
        logger.error(traceback.format_exc())

@receiver(post_save, sender=App)
def check_app_creation_completed(sender, instance, **kwargs):
    try:
        if (instance.is_dynamic_model_created and
            instance.is_dynamic_function_created and
            instance.is_project_structure_created and
            not instance.is_app_created_completed):
            instance.is_app_created_completed = True
            instance.save(update_fields=['is_app_created_completed'])
            logger.info(f"App creation completed for App {instance.id}")
    except Exception as e:
        logger.error(f"Error in check_app_creation_completed: {str(e)}")
        logger.error(traceback.format_exc())

@receiver(post_save, sender=DynamicModel)
def reset_dynamic_model_flag(sender, instance, **kwargs):
    try:
        app = instance.app
        if app.dynamic_models.count() == 0:
            app.is_dynamic_model_created = False
            app.save(update_fields=['is_dynamic_model_created'])
            logger.info(f"Reset is_dynamic_model_created flag for App {app.id}")
    except Exception as e:
        logger.error(f"Error in reset_dynamic_model_flag: {str(e)}")
        logger.error(traceback.format_exc())

@receiver(post_save, sender=DynamicFunction)
def reset_dynamic_function_flag(sender, instance, **kwargs):
    try:
        if instance.app:
            app = instance.app
            if app.dynamic_functions.count() == 0:
                app.is_dynamic_function_created = False
                app.save(update_fields=['is_dynamic_function_created'])
                logger.info(f"Reset is_dynamic_function_created flag for App {app.id}")
    except Exception as e:
        logger.error(f"Error in reset_dynamic_function_flag: {str(e)}")
        logger.error(traceback.format_exc())

@receiver(post_save, sender=ProjectStructure)
def reset_project_structure_flag(sender, instance, **kwargs):
    try:
        app = instance.app
        try:
            app.project_structure
        except ProjectStructure.DoesNotExist:
            app.is_project_structure_created = False
            app.save(update_fields=['is_project_structure_created'])
            logger.info(f"Reset is_project_structure_created flag for App {app.id}")
    except Exception as e:
        logger.error(f"Error in reset_project_structure_flag: {str(e)}")
        logger.error(traceback.format_exc())