# core/management/commands/create_function.py

import json
from django.core.management.base import BaseCommand
from django.conf import settings
from space.models import Space, SpaceFeed, SpaceDataSource
from user.models import OnboardingStepTemplate
from webhook.models import ExternalApiUrl, WebhookSetting
from webhook.models import AIModelProvider, AIModel
from webhook.models import Endpoint, Function, Intent, FunctionAgent

class Command(BaseCommand):
    help = 'Create Endpoint, Function, and FunctionAgent for create-space API'

    def handle(self, *args, **kwargs):
        # Create or get the Endpoint
        endpoint, created = Endpoint.objects.get_or_create(
            base_url='https://dev.withgpt.com/api/v1',
            url='/onboarding/user/space/create-space/',
            method='POST',
            defaults={
                'name': 'Create Space',
                'description': 'API to create a new space',
                'requires_authentication': True,
                'payload_structure': {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the space"
                        },
                        "space_type": {
                            "type": "string",
                            "description": "Type of the space",
                            "enum": ["personal", "work"]
                        }
                    },
                    "required": ["name", "space_type"]
                },
                'response_structure': {
                    "status": 201,
                    "message": "Space created successfully",
                    "data": {
                        "space_id": "string",
                        "name": "string",
                        "time_zone": "string",
                        "feed_types": [
                            {
                                "id": "string",
                                "name": "string"
                            }
                        ]
                    }
                }
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Endpoint: {endpoint}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Endpoint already exists: {endpoint}'))

        # Create or get the Function
        function, created = Function.objects.get_or_create(
            name='create_space',
            endpoint=endpoint,
            defaults={
                'description': 'API to create a new space',
                'ui_component': 'SpaceCreationForm',
                'input_parameters': {
                    "name": "string",
                    "space_type": "personal"
                },
                'output_structure': {
                    "status": 201,
                    "message": "Space created successfully",
                    "data": {
                        "space_id": "string",
                        "name": "string",
                        "time_zone": "string",
                        "feed_types": [
                            {
                                "id": "string",
                                "name": "string"
                            }
                        ]
                    }
                },
                'parameters': {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the space"
                        },
                        "space_type": {
                            "type": "string",
                            "description": "Type of the space",
                            "enum": ["personal", "work"]
                        }
                    },
                    "required": ["name", "space_type"]
                }
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Function: {function}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Function already exists: {function}'))

        # Create or get the FunctionAgent
        function_agent, created = FunctionAgent.objects.get_or_create(
            name='Create Space Agent',
            function=function,
            defaults={
                'description': 'Agent to handle the creation of spaces',
                'requires_authentication': True,
                'ai_model_provider': AIModelProvider.objects.first(),  # Assuming you have at least one AIModelProvider
                'ai_model': AIModel.objects.first(),  # Assuming you have at least one AIModel
                'instructions': 'Create a new space using the provided parameters.'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created FunctionAgent: {function_agent}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'FunctionAgent already exists: {function_agent}'))