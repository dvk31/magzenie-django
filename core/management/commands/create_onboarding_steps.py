# your_app/management/commands/create_onboarding_steps.py

import os
import json
import logging
import traceback
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from user.models import OnboardingStepTemplate
from webhook.models import Endpoint

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Match existing URLs to OnboardingStepTemplate and create missing Endpoints.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making any changes.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        json_file_path = os.path.join(settings.BASE_DIR, '..', 'user', 'models', 'onboarding_steps.json')
        try:
            self.process_onboarding_steps(json_file_path, dry_run)
        except Exception as e:
            logger.error('An error occurred: %s', str(e))
            logger.error(traceback.format_exc())

    @transaction.atomic
    def process_onboarding_steps(self, json_file_path, dry_run):
        try:
            with open(json_file_path, 'r') as file:
                file_content = file.read().strip()
                if not file_content:
                    raise ValueError(f"The file {json_file_path} is empty.")
                steps_data = json.loads(file_content)
        except FileNotFoundError:
            logger.error(f"The file {json_file_path} does not exist.")
            return
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from file {json_file_path}: {e}")
            return
        except ValueError as e:
            logger.error(str(e))
            return
        
        for step_data in steps_data:
            try:
                self.process_step_data(step_data, dry_run)
            except Exception as e:
                logger.error('Failed to process step %s: %s', step_data.get('step'), str(e))
                logger.error(traceback.format_exc())
                raise

    def process_step_data(self, step_data, dry_run):
        logger.info(f"Processing step: {step_data['step']}")
        
        step, created = OnboardingStepTemplate.objects.get_or_create(
            step=step_data['step'],
            defaults={'form_structure': step_data.get('form_structure')}
        )
        
        if created:
            logger.info(f"Created new OnboardingStepTemplate: {step_data['step']}")
        else:
            logger.info(f"Found existing OnboardingStepTemplate: {step_data['step']}")
            if step_data.get('form_structure'):
                step.form_structure = step_data['form_structure']
                if not dry_run:
                    step.save()
                    logger.info(f"Updated form_structure for step: {step_data['step']}")

        endpoint_data = step_data.get('endpoint')
        if endpoint_data:
            endpoint = self.find_or_create_endpoint(endpoint_data, step, dry_run)
            step.endpoint = endpoint

        next_step_name = step_data.get('next_step')
        if next_step_name:
            next_step, next_created = OnboardingStepTemplate.objects.get_or_create(step=next_step_name)
            step.next_step = next_step
            if next_created:
                logger.info(f"Created next OnboardingStepTemplate: {next_step_name}")
            else:
                logger.info(f"Found existing next OnboardingStepTemplate: {next_step_name}")

        if not dry_run:
            step.save()
            logger.info(f"Saved OnboardingStepTemplate: {step_data['step']}")

    def find_or_create_endpoint(self, endpoint_data, step, dry_run):
        logger.info(f"Processing endpoint for step: {step.step}")
        
        endpoint, created = Endpoint.objects.get_or_create(
            url=endpoint_data['url'],
            defaults={
                'name': endpoint_data['name'],
                'method': endpoint_data['method'],
                'description': endpoint_data['description'],
                'payload_structure': endpoint_data.get('payload_structure'),
                'response_structure': endpoint_data.get('response_structure')
            }
        )

        if created:
            logger.info(f"Created new Endpoint: {endpoint_data['url']}")
            endpoint.to_do = True
        else:
            logger.info(f"Found existing Endpoint: {endpoint_data['url']}")
            if endpoint_data.get('payload_structure'):
                endpoint.payload_structure = endpoint_data['payload_structure']
            if endpoint_data.get('response_structure'):
                endpoint.response_structure = endpoint_data['response_structure']
            if endpoint_data.get('description'):
                endpoint.description = endpoint_data['description']

        endpoint.onboarding_step = step

        if not dry_run:
            endpoint.save()
            logger.info(f"Saved Endpoint: {endpoint_data['url']}")

        return endpoint