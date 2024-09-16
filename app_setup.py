import os


def create_app_folders(app_name):
    base_path = os.path.join(os.getcwd(), app_name)
    os.makedirs(base_path, exist_ok=True)

    # List of folders to be created
    folders = [
        "models",
        "views",
        "forms",
        "templates",
        "api",
        "utils",
        "tests",
        "management/commands",
        "static",
    ]

    # Create folders
    for folder in folders:
        os.makedirs(os.path.join(base_path, folder), exist_ok=True)

    # List of files to be created
    files = [
        "forms/forms.py",
        "templates/{}.html".format(app_name),
        "tests/__init__.py",
        "tests/test_models.py",
        "tests/test_views.py",
        "tests/test_forms.py",
        "signals.py",
        "urls.py",
    ]

    model_file = f"models/{app_name}_model.py"
    view_file = f"views/{app_name}_view.py"
    api_view_file = f"api/{app_name}_api_view.py"
    serializer_file = f"api/{app_name}_api_serializer.py"

    files.extend([model_file, view_file, api_view_file, serializer_file])

    # Create files
    for file in files:
        open(os.path.join(base_path, file), "a").close()

    # Create __init__.py files for models and views
    with open(os.path.join(base_path, "models/__init__.py"), "w") as f:
        f.write(f"from .{app_name}_model import {app_name.capitalize()}Model\n")

    with open(os.path.join(base_path, "views/__init__.py"), "w") as f:
        f.write(f"from .{app_name}_view import {app_name.capitalize()}View\n")

    # Create a basic model
    with open(os.path.join(base_path, model_file), "w") as f:
        f.write(
            f"""from django.db import models

class {app_name.capitalize()}Model(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
"""
        )

    # Create a basic view
    with open(os.path.join(base_path, view_file), "w") as f:
        f.write(
            f"""from django.shortcuts import render
from .models import {app_name.capitalize()}Model

class {app_name.capitalize()}View:
    def get(self, request):
        {app_name}_objects = {app_name.capitalize()}Model.objects.all()
        return render(request, '{app_name}/{app_name}.html', {{'{app_name}_objects': {app_name}_objects}})
"""
        )

    # Create a basic API view and serializer
    with open(os.path.join(base_path, api_view_file), "w") as f:
        f.write(
            f"""from rest_framework import generics
from .models import {app_name.capitalize()}Model
from .{app_name}_api_serializer import {app_name.capitalize()}Serializer

class {app_name.capitalize()}APIView(generics.ListCreateAPIView):
    queryset = {app_name.capitalize()}Model.objects.all()
    serializer_class = {app_name.capitalize()}Serializer
"""
        )

    with open(os.path.join(base_path, serializer_file), "w") as f:
        f.write(
            f"""from rest_framework import serializers
from .models import {app_name.capitalize()}Model

class {app_name.capitalize()}Serializer(serializers.ModelSerializer):
    class Meta:
        model = {app_name.capitalize()}Model
        fields = '__all__'
"""
        )


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    app_name = input("Enter the app name: ")
    create_app_folders(app_name)

    logging.info(f"App '{app_name}' folder structure created.")