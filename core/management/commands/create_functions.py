# core/management/commands/create_function.py

import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from space.models import Space, SpaceFeed, SpaceDataSource
from user.models import OnboardingStepTemplate
from webhook.models import ExternalApiUrl, WebhookSetting
from webhook.models import AIModelProvider, AIModel
from webhook.models import Endpoint, Function, Intent, FunctionAgent

class Command(BaseCommand):
    help = 'Create Endpoint, Function, and FunctionAgent from JSON configuration'

    def handle(self, *args, **kwargs):
        config_path = os.path.join(settings.BASE_DIR, 'function_config.json')
        
        if not os.path.exists(config_path):
            self.stdout.write(self.style.ERROR('Configuration file not found'))
            return
        
        with open(config_path, 'r') as file:
            config = json.load(file)
        
        for function_config in config.get('functions', []):
            self.create_endpoint(function_config['endpoint'])
            self.create_function(function_config['function'], function_config['endpoint'])

    def create_endpoint(self, endpoint_config):
        endpoint, created = Endpoint.objects.get_or_create(
            base_url=endpoint_config['base_url'],
            url=endpoint_config['url'],
            method=endpoint_config['method'],
            defaults={
                'name': endpoint_config['name'],
                'description': endpoint_config['description'],
                'requires_authentication': endpoint_config['requires_authentication'],
                'payload_structure': endpoint_config['payload_structure'],
                'response_structure': endpoint_config['response_structure']
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Endpoint: {endpoint}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Endpoint already exists: {endpoint}'))

    def create_function(self, function_config, endpoint_config):
        endpoint = Endpoint.objects.get(
            base_url=endpoint_config['base_url'],
            url=endpoint_config['url'],
            method=endpoint_config['method']
        )
        
        function, created = Function.objects.get_or_create(
            name=function_config['name'],
            endpoint=endpoint,
            defaults={
                'description': function_config['description'],
                'ui_component': function_config['ui_component'],
                'input_parameters': function_config['input_parameters'],
                'output_structure': function_config['output_structure'],
                'parameters': function_config['parameters']
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Function: {function}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Function already exists: {function}'))