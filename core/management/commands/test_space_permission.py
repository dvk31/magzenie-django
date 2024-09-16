import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from space.models import Space, SpaceMember, Role

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'List spaces and roles for a user given their token or UUID'

    def add_arguments(self, parser):
        parser.add_argument('identifier', type=str, help='JWT token or UUID of the user')

    def handle(self, *args, **options):
        identifier = options['identifier']
        User = get_user_model()

        try:
            # Determine if the identifier is a token or a UUID
            if len(identifier) == 40:  # Simple check for token length
                # Decode the token to get the user
                access_token = AccessToken(identifier)
                user_id = access_token['user_id']
                user = User.objects.get(id=user_id)
                logger.info(f"User ID from token: {user.id}")
            else:
                # Treat identifier as a UUID
                user = User.objects.get(id=identifier)
                logger.info(f"User ID from UUID: {user.id}")

            # List spaces and roles
            spaces = Space.objects.all()
            user_spaces = []

            for space in spaces:
                is_owner = space.owner == user

                try:
                    space_member = SpaceMember.objects.get(user=user, space=space)
                    is_admin = space_member.role.name == 'admin'
                except SpaceMember.DoesNotExist:
                    is_admin = False

                if is_owner or is_admin:
                    user_spaces.append({
                        'space_id': space.id,
                        'space_name': space.name,
                        'is_owner': is_owner,
                        'is_admin': is_admin
                    })

                    logger.debug(f"Space ID: {space.id}, Space Name: {space.name}, Is Owner: {is_owner}, Is Admin: {is_admin}")

            if user_spaces:
                self.stdout.write(self.style.SUCCESS(f"User {user.id} is associated with the following spaces:"))
                for space_info in user_spaces:
                    self.stdout.write(f"Space ID: {space_info['space_id']}, Space Name: {space_info['space_name']}, Is Owner: {space_info['is_owner']}, Is Admin: {space_info['is_admin']}")
            else:
                self.stdout.write(self.style.WARNING(f"User {user.id} is not associated with any spaces as owner or admin."))

        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))