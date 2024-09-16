# myapp/management/commands/initialize_user_supabase.py

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from user.models import SupabaseInstance, App, DynamicModel, AIAgent, AIAgentTool, IntentMetadata, AIAgentMetadata
from user.services.supabase_service import SupabaseService
import uuid
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Initialize Supabase instance for a user and create necessary tables and records'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=uuid.UUID, help='UUID of the user to initialize Supabase for')

    def handle(self, *args, **options):
        user_id = options['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f'User with ID {user_id} does not exist')

        try:
            with transaction.atomic():
                supabase_instance = self.get_or_create_supabase_instance(user)
                supabase_service = SupabaseService(supabase_instance)
                
                if not supabase_instance.is_initialized:
                    supabase_service.initialize_instance()
                    self.stdout.write(self.style.SUCCESS(f'Successfully initialized Supabase for user {user.username}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Supabase instance for user {user.username} is already initialized'))

        except Exception as e:
            logger.error(f"Error initializing Supabase for user {user.username}: {str(e)}")
            raise CommandError(f'Failed to initialize Supabase: {str(e)}')

    def get_or_create_supabase_instance(self, user):
        supabase_instance, created = SupabaseInstance.objects.get_or_create(
            user=user,
            defaults={
                'project_ref': f'user-{user.id}-{uuid.uuid4().hex[:8]}',
                'project_id': str(uuid.uuid4()),
                'db_password': uuid.uuid4().hex,
                'db_user': f'user_{user.id}',
                'port': 5432,
                'instance_url': f'https://{uuid.uuid4().hex[:8]}.supabase.co',
                'service_role_secret': uuid.uuid4().hex,
                'public_non_key': uuid.uuid4().hex,
                'is_initialized': False
            }
        )
        if created:
            logger.info(f"Created new SupabaseInstance for user {user.username}")
        return supabase_instance

    def initialize_supabase_instance(self, supabase_service):
        supabase_service.initialize_instance()
        logger.info("Initialized Supabase instance with default tables and functions")

    def create_default_app(self, user, supabase_instance):
        app, created = App.objects.get_or_create(
            user=user,
            supabase_instance=supabase_instance,
            name='Default App',
            defaults={'supabase_id': str(uuid.uuid4())}
        )
        if created:
            logger.info(f"Created default App for user {user.username}")
        return app

    def create_default_dynamic_models(self, app, supabase_service):
        default_models = [
            {
                'name': 'User',
                'schema': {
                    'name': 'text',
                    'email': 'text',
                    'age': 'integer'
                }
            },
            {
                'name': 'Product',
                'schema': {
                    'name': 'text',
                    'price': 'numeric',
                    'description': 'text'
                }
            }
        ]

        for model in default_models:
            dynamic_model, created = DynamicModel.objects.get_or_create(
                app=app,
                name=model['name'],
                defaults={
                    'schema': model['schema'],
                    'supabase_table_name': f"{app.name.lower()}_{model['name'].lower()}",
                    'api_endpoint': f"{app.supabase_instance.instance_url}/rest/v1/{app.name.lower()}_{model['name'].lower()}"
                }
            )
            if created:
                supabase_service.create_table(dynamic_model.supabase_table_name, [
                    {'name': 'id', 'type': 'uuid', 'primary': True},
                    *[{'name': k, 'type': v} for k, v in model['schema'].items()]
                ])
                logger.info(f"Created DynamicModel {model['name']} for app {app.name}")

    def create_ai_agent(self, app):
        ai_agent, created = AIAgent.objects.get_or_create(
            app=app,
            defaults={
                'supabase_id': str(uuid.uuid4()),
                'name': f'{app.name} Agent',
                'description': f'AI Agent for {app.name}',
                'is_active': True
            }
        )
        if created:
            logger.info(f"Created AIAgent for app {app.name}")

        for dynamic_model in app.dynamic_models.all():
            for tool_type, _ in AIAgentTool.tool_type.field.choices:
                AIAgentTool.objects.get_or_create(
                    agent=ai_agent,
                    dynamic_model=dynamic_model,
                    tool_type=tool_type,
                    defaults={
                        'supabase_id': str(uuid.uuid4()),
                        'name': f'{tool_type.capitalize()} {dynamic_model.name}',
                        'description': f'{tool_type.capitalize()} operation for {dynamic_model.name}'
                    }
                )
        logger.info(f"Created AIAgentTools for AIAgent of app {app.name}")

    def create_metadata(self, app):
        IntentMetadata.objects.get_or_create(
            app=app,
            name='Default Intent',
            defaults={'supabase_function_name': 'process_default_intent'}
        )
        logger.info(f"Created IntentMetadata for app {app.name}")

        AIAgentMetadata.objects.get_or_create(
            app=app,
            name='Default AI Agent Metadata',
            defaults={'supabase_function_name': 'process_default_ai_agent'}
        )
        logger.info(f"Created AIAgentMetadata for app {app.name}")