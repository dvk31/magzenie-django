from django.core.management.base import BaseCommand
from django.conf import settings
from supabase import create_client, Client
from django.contrib.auth import get_user_model
from users.models import UserProfile
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser in Supabase and a corresponding UserProfile in Django'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the superuser')
        parser.add_argument('password', type=str, help='Password for the superuser')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']

        logger.info(f"Attempting to create superuser with email: {email}")

        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        try:
            # Create user in Supabase
            user = supabase.auth.admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': True,
                'app_metadata': {'role': 'supabase_admin'}
            })

            if user:
                logger.info(f"Successfully created superuser in Supabase: {email}")

                # Create or get the user in Django
                django_user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'is_super_admin': True,
                        'is_staff': True,
                        'is_superuser': True,
                    }
                )

                if created:
                    logger.info(f"Created new Django user for: {email}")
                else:
                    logger.info(f"Retrieved existing Django user for: {email}")

                # Create UserProfile
                profile, profile_created = UserProfile.objects.get_or_create(
                    user=django_user,
                    defaults={
                        'bio': 'Superuser profile',
                        'is_staff': True,
                        'is_superuser': True,
                        'is_active': True,
                    }
                )

                if profile_created:
                    logger.info(f"Created new UserProfile for: {email}")
                else:
                    logger.info(f"Retrieved existing UserProfile for: {email}")

                self.stdout.write(self.style.SUCCESS(f'Successfully created superuser and profile: {email}'))
            else:
                logger.error("Failed to create superuser. User object is None.")
                self.stdout.write(self.style.ERROR('Failed to create superuser'))
        except Exception as e:
            logger.exception(f"An error occurred while creating superuser: {str(e)}")
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))