# project_root/dynamic_api.py

from django.apps import apps
from rest_framework import serializers, viewsets, routers
from django.urls import path, include

# Initialize the router
router = routers.DefaultRouter()

# List of app names you want to generate APIs for
APP_NAMES = [
    'magazines',
    'payments',
    'analytics',
    'notifications',
    'support',
    'media',
    'users',
    'print_orders',
    'digital_setup',
    'core',
]

def generate_api_for_app(app_name):
    app_models = apps.get_app_config(app_name).get_models()
    
    for model in app_models:
        # Skip unmanaged models
        if not model._meta.managed:
            continue

        # Dynamically create a serializer
        serializer_meta = type('Meta', (), {
            'model': model,
            'fields': '__all__'
        })
        serializer_class = type(
            f'{model.__name__}Serializer',
            (serializers.ModelSerializer,),
            {'Meta': serializer_meta}
        )

        # Dynamically create a viewset
        viewset_class = type(
            f'{model.__name__}ViewSet',
            (viewsets.ModelViewSet,),
            {
                'queryset': model.objects.all(),
                'serializer_class': serializer_class,
                'http_method_names': ['get', 'post', 'put', 'patch', 'delete'],
                # Optionally add permission classes
                # 'permission_classes': [YourPermissionClass],
            }
        )

        # Register the viewset with the router
        router.register(
            f'{app_name}/{model._meta.model_name}',
            viewset_class,
            basename=f'{app_name}-{model._meta.model_name}'
        )

# Generate API for each app
for app_name in APP_NAMES:
    generate_api_for_app(app_name)

# Generate the URL patterns
urlpatterns = [
    path('', include(router.urls)),
]