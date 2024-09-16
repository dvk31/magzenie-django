import os
import inspect
from django.core.management.base import BaseCommand
from django.apps import apps
import core.serializers as serializers_module
from rest_framework import serializers
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate viewsets based on serializers defined in core.serializers'

    def handle(self, *args, **options):
        self.generate_viewsets()

    def generate_viewsets(self):
        serializer_classes = [
            member for name, member in inspect.getmembers(serializers_module)
            if inspect.isclass(member) and issubclass(member, serializers.ModelSerializer)
        ]

        views_file_path = os.path.join(os.path.dirname(inspect.getfile(serializers_module)), 'views.py')

        with open(views_file_path, 'w') as file:
            file.write("import logging\n")
            file.write("from django.db import transaction\n")
            file.write("from rest_framework import status\n")
            file.write("from rest_framework.response import Response\n")
            file.write("from core.common.base_viewset import BaseViewSet\n")
            file.write("from rest_framework.authentication import TokenAuthentication\n")
            file.write("from rest_framework.permissions import IsAuthenticated\n\n")

            imported_models = set()
            imported_serializers = set()

            for serializer_class in serializer_classes:
                model_class = serializer_class.Meta.model
                app_label = model_class._meta.app_label
                model_name = model_class.__name__
                serializer_name = serializer_class.__name__

                if model_name not in imported_models:
                    file.write(f"from {app_label}.models import {model_name}\n")
                    imported_models.add(model_name)

                if serializer_name not in imported_serializers:
                    file.write(f"from core.serializers import {serializer_name}\n")
                    imported_serializers.add(serializer_name)

                viewset_class_name = f"{model_name}ViewSet"
                file.write(f"\nclass {viewset_class_name}(BaseViewSet):\n")
                file.write(f"    queryset = {model_name}.objects.all()\n")
                file.write(f"    serializer_class = {serializer_name}\n")
                file.write(f"    authentication_classes = [TokenAuthentication]\n")
                file.write(f"    permission_classes = [IsAuthenticated]\n\n")
                
                # Example of wrapping create method with transaction
                file.write(f"    def create(self, request, *args, **kwargs):\n")
                file.write(f"        with transaction.atomic():\n")
                file.write(f"            return super().create(request, *args, **kwargs)\n\n")

        logger.info(f"Viewsets generated successfully at {views_file_path}.")