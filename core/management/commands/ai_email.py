from django.core.management.base import BaseCommand
from django.conf import settings
from celery import Celery
from emails.models import EmailMessage
from emails.signals import process_new_email

import logging

class Command(BaseCommand):
    help = 'Process emails using Celery'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        try:
            self.logger.debug("Creating a Celery app instance.")
            # Create a Celery app instance
            app = Celery('myapp', broker=settings.CELERY_BROKER_URL)

            self.logger.debug("Fetching unprocessed emails.")
            # Get all unprocessed emails
            unprocessed_emails = EmailMessage.objects.filter(email_analyzed=False)

            email_count = unprocessed_emails.count()
            self.stdout.write(self.style.SUCCESS(f'Found {email_count} unprocessed emails.'))
            self.logger.info(f'Found {email_count} unprocessed emails ready for processing.')

            # Process each unprocessed email using Celery
            for email in unprocessed_emails:
                self.stdout.write(self.style.SUCCESS(f'Processing email with ID: {email.id}'))
                self.logger.info(f'Queueing email with ID: {email.id} for processing.')
                process_new_email.delay(email.id)

            self.stdout.write(self.style.SUCCESS('Email processing tasks have been queued.'))
            self.logger.info('All unprocessed emails have been queued for processing.')

        except Exception as e:
            error_message = f'Error processing emails: {str(e)}'
            self.stdout.write(self.style.ERROR(error_message))
            self.logger.error(error_message)
