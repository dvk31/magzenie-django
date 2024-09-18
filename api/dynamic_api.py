# api/dynamic_api.py

from django.apps import apps
from rest_framework import serializers, viewsets, routers
from django.urls import path, include
from collections import defaultdict

# Initialize routers for each category
routers = defaultdict(routers.DefaultRouter)

# List of app names you want to generate APIs for
APP_CATEGORIES = {
    'content': ['magazines', 'media'],
    'commerce': ['payments', 'print_orders'],
    'analytics': ['analytics'],
    'user_management': ['users', 'notifications'],
    'operations': ['support', 'digital_setup'],
    'core': ['core']
}

def generate_api_for_app(app_name, category):
    try:
        app_models = apps.get_app_config(app_name).get_models()
    except LookupError:
        print(f"Warning: App '{app_name}' not found. Skipping API generation for this app.")
        return

    for model in app_models:
        if not model._meta.managed:
            continue

        serializer_meta = type('Meta', (), {
            'model': model,
            'fields': '__all__'
        })
        serializer_class = type(
            f'{model.__name__}Serializer',
            (serializers.ModelSerializer,),
            {'Meta': serializer_meta}
        )

        viewset_class = type(
            f'{model.__name__}ViewSet',
            (viewsets.ModelViewSet,),
            {
                'queryset': model.objects.all(),
                'serializer_class': serializer_class,
                'http_method_names': ['get', 'post', 'put', 'patch', 'delete'],
                # 'permission_classes': [YourPermissionClass],
            }
        )

        # Register the viewset with the appropriate category router
        routers[category].register(
            f'{model._meta.model_name}',
            viewset_class,
            basename=f'{app_name}-{model._meta.model_name}'
        )

# Generate API for each app in each category
for category, apps_list in APP_CATEGORIES.items():
    for app_name in apps_list:
        generate_api_for_app(app_name, category)

# Generate the URL patterns
dynamic_api_urlpatterns = [
    path(f'{category}/', include(router.urls)) for category, router in routers.items()
]

