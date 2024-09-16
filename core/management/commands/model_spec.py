import json
import os
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.utils.translation import gettext_lazy
import re


from django.contrib.contenttypes.fields import GenericForeignKey

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
import os
import json


def custom_serializer(obj):
    if hasattr(obj, "__proxy__"):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


# The Command class
class Command(BaseCommand):
    help = "Generate enhanced JSON representation of serializers for all models in a given app"

    def add_arguments(self, parser):
        parser.add_argument(
            "appname",
            type=str,
            help="The name of the app for which to generate serializer JSON",
        )

    def get_field_type(self, field):
        if isinstance(field, models.ForeignKey):
            return "ForeignKey"
        elif isinstance(field, models.OneToOneField):
            return "OneToOneField"
        elif isinstance(field, models.ManyToManyField):
            return "ManyToManyField"
        else:
            return type(field).__name__
    def get_filtering_options(self, field):
        """
        Return a list of filtering options based on the field type.
        """
        field_type = self.get_field_type(field)
        if field_type in ["CharField", "TextField"]:
            return ["exact", "icontains", "istartswith", "iendswith"]
        elif field_type in ["IntegerField", "FloatField", "DecimalField"]:
            return ["exact", "lt", "lte", "gt", "gte", "range"]
        elif field_type in ["DateField", "DateTimeField"]:
            return ["exact", "date", "year", "month", "day", "range"]
        elif field_type in ["BooleanField"]:
            return ["exact"]
        # ... add other field types as necessary
        else:
            return []

    def parse_help_text(self, help_text):
        annotations = {}
        
        if "searchable" in help_text:
            annotations["searchable"] = True
        
        if "default_page_size:" in help_text:
            size = re.search(r"default_page_size:(\d+)", help_text).group(1)
            annotations["default_page_size"] = int(size)
        
        if "custom_endpoint_behavior" in help_text:
            annotations["custom_behavior"] = True
        
        if "choices_field" in help_text:
            annotations["is_choices_field"] = True

        return annotations

    def generate_serializer_json(self, model_class):
        print(f"Processing model: {model_class.__name__}")  # Debug print
        serializer_data = {}
        serializer_data["fields"] = []
        
        # Handle model_metadata
        if hasattr(model_class, "model_metadata"):
            serializer_data["metadata"] = model_class.model_metadata

        # List of sensitive fields that should not be exposed
        sensitive_fields = ["password", "is_superuser"]

        # Check for custom read_only_fields and write_only_fields in the model
        read_only_fields = getattr(model_class, "read_only_fields", [])
        write_only_fields = getattr(model_class, "write_only_fields", [])
        print(f"Read-only fields: {read_only_fields}")

        for field in model_class._meta.get_fields():
            field_data = {}

            # Skip reverse relations and GenericForeignKey
            if (
                field.auto_created
                and not field.concrete
                or isinstance(field, GenericForeignKey)
            ):
                continue

            # Basic Field Information
            field_data["name"] = field.name
            field_data["type"] = self.get_field_type(field)
            field_data["filtering"] = self.get_filtering_options(field)

            # Determine if the field is required
            if hasattr(field, "null") and hasattr(field, "blank"):
                field_data["required"] = not (field.null or field.blank)

            # Mark sensitive fields
            field_data["sensitive"] = field.name in sensitive_fields

            # Read-Only and Write-Only Status
            field_data["read_only"] = (
                isinstance(field, models.AutoField)
                or (
                    isinstance(field, models.DateTimeField)
                    and (field.auto_now or field.auto_now_add)
                )
                or field.name in read_only_fields
            )
            field_data["write_only"] = field.name in write_only_fields

            # Additional attributes
            for attr in [
                "unique",
                "editable",
                "max_length",
                "default",
                "choices",
                "help_text",
                "db_index",
            ]:
                if hasattr(field, attr):
                    value = getattr(field, attr)

                    print(
                        f"Debug: attr = {attr}, value = {value}, type(value) = {type(value)}"
                    )  # Debug line

                    # Force evaluation of lazy translation objects
                    if isinstance(value, type(gettext_lazy(""))):
                        value = str(value)

                    # Convert non-JSON serializable types to strings
                    elif callable(value) or isinstance(value, type):
                        value = str(value)

                    field_data[attr] = value

            # Capture auto_now and auto_now_add for DateTimeField
            if isinstance(field, models.DateTimeField):
                for attr in ["auto_now", "auto_now_add"]:
                    if hasattr(field, attr):
                        field_data[attr] = getattr(field, attr)

            # Capture on_delete, null, and blank for relationship fields
            if isinstance(field, (models.ForeignKey, models.ManyToManyField)):
                for attr in ["on_delete", "null", "blank"]:
                    if hasattr(field, attr):
                        field_data[attr] = (
                            getattr(field, attr).__name__
                            if attr == "on_delete"
                            else getattr(field, attr)
                        )

            # Nested Serializer Information
            if field_data["type"] in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
                related_model = field.related_model
                field_data["nested_serializer"] = f"{related_model.__name__}Serializer"

                # Include the module where the related serializer is likely defined.
                field_data[
                    "nested_serializer_module"
                ] = f"{model_class._meta.app_label}.serializers"

                related_name = getattr(field.remote_field, "related_name", None)
                if related_name:
                    field_data["related_name"] = related_name
                    
            # Handle help_text annotations
            annotations = self.parse_help_text(field.help_text)
            field_data.update(annotations)

            serializer_data["fields"].append(field_data)

        return {f"{model_class.__name__}Model": serializer_data}

    def handle(self, *args, **kwargs):
        appname = kwargs["appname"]
        try:
            app_config = apps.get_app_config(appname)
        except LookupError:
            raise CommandError(f"App '{appname}' does not exist.")

        output_json = {}
        for model in app_config.get_models():
            output_json.update(self.generate_serializer_json(model))

        # Ensure the 'generated' directory exists
        generated_dir = os.path.join(appname, "generated")
        os.makedirs(generated_dir, exist_ok=True)

        # Write to serializers.json
        output_file_path = os.path.join(generated_dir, "model_schema.json")
        with open(output_file_path, "w") as f:
            json.dump(output_json, f, indent=4, default=custom_serializer)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated enhanced serializer JSON for app "{appname}"'
            )
        )