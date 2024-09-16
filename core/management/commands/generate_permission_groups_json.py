from django.core.management.base import BaseCommand
from django.apps import apps
import json
import os

class Command(BaseCommand):
    help = 'Generates a JSON file of permission groups based on models related to TryoutSpace'

    def handle(self, *args, **options):
        output_file = 'permission_groups.json'
        tryoutspace_model = apps.get_model('tryoutspace', 'TryoutSpace')
        related_models = self.get_related_models(tryoutspace_model)
        permission_groups = self.generate_permission_groups(related_models)
        json_template = {
            'permission_groups': permission_groups,
        }

        # Write the JSON template to the file in the root directory
        with open(output_file, 'w') as f:
            json.dump(json_template, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'Permission groups JSON file generated: {output_file}'))

    def get_related_models(self, model, visited_models=None):
        if visited_models is None:
            visited_models = set()

        related_models = []
        for field in model._meta.get_fields():
            if field.is_relation and field.related_model != model and field.related_model not in visited_models:
                related_model = field.related_model
                related_models.append(related_model)
                visited_models.add(related_model)
                related_models.extend(self.get_related_models(related_model, visited_models))

        return related_models

    def generate_permission_groups(self, models):
        permission_groups = []
        for model in models:
            model_name = model._meta.model_name
            group_name = f"{model_name.capitalize()} Management"
            permission_codenames = [
                f'view_{model_name}',
                f'add_{model_name}',
                f'change_{model_name}',
                f'delete_{model_name}',
            ]
            permissions = [
                {
                    'codename': codename,
                    'name': f"Can {codename.split('_')[0]} {model_name}",
                }
                for codename in permission_codenames
            ]
            permission_group = {
                'name': group_name,
                'permissions': permissions,
            }
            permission_groups.append(permission_group)
        return permission_groups