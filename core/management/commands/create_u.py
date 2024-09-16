import os
import inspect
from django.core.management.base import BaseCommand
from django.urls import path, include
from rest_framework.routers import DefaultRouter
import core.views as views_module
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate or update URLs based on viewsets defined in core.views'

    def handle(self, *args, **options):
        self.generate_urls()

    def generate_urls(self):
        viewset_classes = [
            member for name, member in inspect.getmembers(views_module)
            if inspect.isclass(member) and issubclass(member, views_module.ModelViewSet)
        ]

        urls_file_path = os.path.join(os.path.dirname(inspect.getfile(views_module)), 'urls.py')

        with open(urls_file_path, 'w') as file:
            file.write("from django.urls import path, include\n")
            file.write("from rest_framework.routers import DefaultRouter\n")

            imported_viewsets = set()

            for viewset_class in viewset_classes:
                viewset_name = viewset_class.__name__

                if viewset_name not in imported_viewsets:
                    file.write(f"from core.views import {viewset_name}\n")
                    imported_viewsets.add(viewset_name)

            file.write("\nrouter = DefaultRouter()\n")

            for viewset_class in viewset_classes:
                if viewset_class.queryset is not None and hasattr(viewset_class.queryset, 'model'):
                    model_name = viewset_class.queryset.model.__name__.lower()
                    file.write(f"router.register(r'{model_name}', {viewset_class.__name__})\n")
                else:
                    logger.warning(f"Skipping {viewset_class.__name__} as it does not have a valid queryset.")

            file.write("\nurlpatterns = [\n")
            file.write("    path('', include(router.urls)),\n")
            file.write("]\n")

        logger.info(f"URLs generated successfully at {urls_file_path}.")