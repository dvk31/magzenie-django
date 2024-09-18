# your_app/dynamic_api.py

from django.apps import apps
from rest_framework import serializers, viewsets, routers
from django.urls import path, include

# Initialize the router
router = routers.DefaultRouter()

# Get all models from the app
app_models = apps.get_app_config('your_app').get_models()

for model in app_models:
    # Skip unmanaged models (e.g., auth.User)
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
        r'{0}'.format(model._meta.model_name),
        viewset_class,
        basename=model._meta.model_name
    )

# Generate the URL patterns
urlpatterns = [
    path('', include(router.urls)),
]
