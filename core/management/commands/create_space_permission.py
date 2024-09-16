import json
import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.db.utils import IntegrityError
from space.models import PermissionGroup, Permission

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create permission groups and permissions from a JSON template'

    def handle(self, *args, **kwargs):
        json_file_path = os.path.join(settings.BASE_DIR, '..', 'space', 'models', 'permission_template.json')
        try:
            data = self.load_json(json_file_path)
            self.create_permission_groups_and_permissions(data)
            self.stdout.write(self.style.SUCCESS('Permission groups and permissions have been successfully created.'))
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {json_file_path}'))
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR('Error decoding JSON file'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An unexpected error occurred: {str(e)}'))
            logger.error(f'An unexpected error occurred: {str(e)}', exc_info=True)

    def load_json(self, file_path):
        with open(file_path, 'r') as file:
            return json.load(file)

    @transaction.atomic
    def create_permission_groups_and_permissions(self, data):
        for group_data in data:
            group = self.get_or_create_permission_group(group_data['name'], group_data['description'])
            for permission_data in group_data['permissions']:
                self.get_or_create_permission(permission_data, group)

    def get_or_create_permission_group(self, group_name, group_description):
        try:
            group, created = PermissionGroup.objects.get_or_create(
                name=group_name,
                defaults={'description': group_description}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission group: {group_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Permission group already exists: {group_name}'))
            return group
        except IntegrityError as e:
            logger.error(f'Error creating permission group {group_name}: {str(e)}', exc_info=True)
            raise

    def get_or_create_permission(self, permission_data, group):
        try:
            perm_name = permission_data['name']
            perm_description = permission_data['description']
            permission, created = Permission.objects.get_or_create(
                name=perm_name,
                defaults={'description': perm_description, 'group': group}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {perm_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Permission already exists: {perm_name}'))
            return permission
        except IntegrityError as e:
            logger.error(f'Error creating permission {perm_name}: {str(e)}', exc_info=True)
            raise