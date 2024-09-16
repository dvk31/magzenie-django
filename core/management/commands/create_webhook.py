import logging
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from webhook.models import WebhookSetting, ModelField, FieldsToWatch, TriggerRule, TriggerCondition
from emails.models import EmailMessage

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create webhook settings and conditions for EmailMessage model'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                webhook_setting = self.create_or_get_webhook_setting()
                content_type = self.get_content_type_for_model()
                fields_to_watch = self.create_or_get_fields_to_watch(content_type)
                trigger_rule = self.create_or_get_trigger_rule(webhook_setting)
                self.create_or_get_trigger_conditions(trigger_rule, fields_to_watch)
                self.stdout.write(self.style.SUCCESS('Successfully created or updated webhook settings and conditions'))
        except Exception as e:
            logger.error(f"Error creating webhook settings and conditions: {str(e)}", exc_info=True)
            self.stdout.write(self.style.ERROR('Failed to create or update webhook settings and conditions'))

    def create_or_get_webhook_setting(self):
        webhook_setting, created = WebhookSetting.objects.get_or_create(
            name="EmailMessage Webhook",
            defaults={
                'url': "https://example.com/webhook",
                'active': True,
                'headers': {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer YOUR_API_KEY"
                }
            }
        )
        logger.info(f"WebhookSetting {'created' if created else 'retrieved'}: {webhook_setting.name}")
        return webhook_setting

    def get_content_type_for_model(self):
        return ContentType.objects.get_for_model(EmailMessage)

    def create_or_get_fields_to_watch(self, content_type):
        is_system_email_field, _ = ModelField.objects.get_or_create(
            content_type=content_type,
            field_name='is_system_email'
        )
        is_lead_field, _ = ModelField.objects.get_or_create(
            content_type=content_type,
            field_name='is_lead'
        )
        fields_to_watch, created = FieldsToWatch.objects.get_or_create(content_type=content_type)
        fields_to_watch.fields.set([is_system_email_field, is_lead_field])
        logger.info(f"FieldsToWatch {'created' if created else 'retrieved'} for content type: {content_type}")
        return fields_to_watch

    def create_or_get_trigger_rule(self, webhook_setting):
        trigger_rule, created = TriggerRule.objects.get_or_create(
            name="EmailMessage Trigger",
            webhook_setting=webhook_setting
        )
        logger.info(f"TriggerRule {'created' if created else 'retrieved'}: {trigger_rule.name}")
        return trigger_rule

    def create_or_get_trigger_conditions(self, trigger_rule, fields_to_watch):
        for field in fields_to_watch.fields.all():
            TriggerCondition.objects.get_or_create(
                trigger_rule=trigger_rule,
                fields_to_watch=fields_to_watch,
                condition="value_equal",
                value_type="boolean",
                boolean_value=True,
                defaults={
                    'text_value': field.field_name  # Set the field name as the text_value
                }
            )