import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sets up the directory structure for a given app"

    def add_arguments(self, parser):
        parser.add_argument(
            "app_name",
            type=str,
            help="Name of the Django app for which the structure should be created",
        )

    def handle(self, *args, **kwargs):
        app_name = kwargs["app_name"]
        result = create_project_structure(app_name)
        self.stdout.write(self.style.SUCCESS(result))


def create_project_structure(app_name: str):
    # Base directories and their inner structures
    directories = {
        f"{app_name}/processing_pipeline": ["__init__.py"],
        f"{app_name}/processing_pipeline/base": [
            "__init__.py",
            "pipeline_step.py",
            "feature_strategy.py",
            "common.py",
        ],
        f"{app_name}/processing_pipeline/ai_processing": ["__init__.py"],
        f"{app_name}/processing_pipeline/crud": ["__init__.py"],
        f"{app_name}/processing_pipeline/intent_extraction": ["__init__.py"],
        f"{app_name}/processing_pipeline/notifications": ["__init__.py"],
        f"{app_name}/processing_pipeline/external_api": ["__init__.py"],
        f"{app_name}/processing_pipeline/event_management": ["__init__.py"],
        f"{app_name}/shared": [
            "__init__.py",
            "validators.py",
            "error_handlers.py",
            "loggers.py",
        ],
        f"{app_name}/tests": [
            "ai_processing_tests.py",
            "crud_tests.py",
            "intent_extraction_tests.py",
        ],
        f"{app_name}/documentation/user_guides": [],
        f"{app_name}/documentation/faqs": [],
        f"{app_name}/analytics": [
            "__init__.py",
            "user_metrics.py",
            "system_metrics.py",
        ],
    }

    # Create directories and files
    for directory, files in directories.items():
        os.makedirs(directory, exist_ok=True)
        for file in files:
            with open(os.path.join(directory, file), "w") as f:
                # Add a basic Python comment for .py files
                if file.endswith(".py"):
                    f.write("# This is a Python file\n")
                pass

    # Create README.md
    with open(f"{app_name}/README.md", "w") as readme:
        readme.write("# Documentation explaining the project structure\n")

    return f"Project structure for '{app_name}' created successfully!"


# Test the function with a sample app name
create_project_structure("my_project")
