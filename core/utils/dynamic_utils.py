# core/dynamic_utils.py or wherever your dynamic serializer logic is placed

from django.conf import settings
from importlib import import_module

def get_serializer_class(model_class, depth=1, exclude_fields=None, include_fields=None):
    class_name = model_class.__name__
    app_label = model_class._meta.app_label
    full_model_name = f"{app_label}.{class_name}"

    # Check settings for predefined serializer or instruction for dynamic generation
    serializer_path = settings.DJANGO_SERIALIZER_CONFIG.get(full_model_name)

    if serializer_path:
        # Import and return the predefined serializer
        module_name, class_name = serializer_path.rsplit('.', 1)
        module = import_module(module_name)
        return getattr(module, class_name)

    # If None or not specified, proceed with dynamic generation
    if exclude_fields is None:
        exclude_fields = []

    # Dynamically create a serializer class
    meta_attrs = {
        'model': model_class,
        'fields': include_fields or '__all__',
        'exclude': exclude_fields,
        'depth': depth
    }
    serializer_attrs = {
        'Meta': type('Meta', (object,), meta_attrs)
    }
    serializer_class_name = f"{class_name}Serializer"
    serializer_class = type(serializer_class_name, (serializers.ModelSerializer,), serializer_attrs)
    return serializer_class