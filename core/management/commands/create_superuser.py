from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User, UserProfile
from django.conf import settings
from supabase import create_client
from supabase.lib.client_options import ClientOptions

class Command(BaseCommand):
    help = 'Creates a superuser in Supabase and Django'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', required=True)

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']

        # Initialize Supabase client
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY, options=ClientOptions(persist_session=False))

        with transaction.atomic():
            try:
                # Create user in Supabase
                response = supabase_client.auth.sign_up({
                    "email": email,
                    "password": password,
                })

                if not response.user:
                    self.stdout.write(self.style.ERROR('Failed to create user in Supabase'))
                    return

                supabase_user = response.user

                # Create or get User in Django
                user, created = User.objects.get_or_create(
                    id=supabase_user.id,
                    email=email
                )

                # Create or update UserProfile
                profile, created = UserProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        'is_staff': True,
                        'is_superuser': True,
                        'is_active': True
                    }
                )

                self.stdout.write(self.style.SUCCESS(f'Successfully created superuser: {email}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))