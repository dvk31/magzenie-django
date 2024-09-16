import json
import os
import ast
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings

class ModelCodeExtractor(ast.NodeVisitor):
    def __init__(self):
        self.classes = {}

    def visit_ClassDef(self, node):
        class_code = self.extract_class_definition(node)
        self.classes[node.name] = class_code

    def extract_base_classes(self, bases):
        base_classes = []
        for base in bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(f"{base.value.id}.{base.attr}")
            else:
                base_classes.append(ast.unparse(base))
        return ', '.join(base_classes)

    def extract_class_definition(self, node):
        class_lines = []
        base_classes = self.extract_base_classes(node.bases)
        class_lines.append(f"class {node.name}({base_classes}):")
        
        for item in node.body:
            if isinstance(item, (ast.AnnAssign, ast.Assign)):
                class_lines.append(f"    {ast.unparse(item)}")
            elif isinstance(item, ast.ClassDef):
                nested_class = self.extract_class_definition(item)
                class_lines.extend(['    ' + line for line in nested_class.split('\n')])

        if len(class_lines) == 1:
            class_lines.append("    pass")

        return '\n'.join(class_lines)

    def extract_model_code(self, source_code):
        tree = ast.parse(source_code)
        self.visit(tree)
        return self.classes

class Command(BaseCommand):
    help = 'Collect all Django models into a single file named model.txt in the project root'

    def add_arguments(self, parser):
        parser.add_argument('--config', type=str, default='model_text.json', help='Path to the configuration file')

    def handle(self, *args, **options):
        config_path = options['config']
        if not os.path.isabs(config_path):
            config_path = os.path.join(settings.BASE_DIR, config_path)

        try:
            with open(config_path, 'r') as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'Configuration file not found: {config_path}'))
            return
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f'Invalid JSON in configuration file: {config_path}'))
            return

        ignore_models = set(config.get('ignore_models', []))

        output_file = os.path.join(settings.BASE_DIR, 'model.txt')
        extractor = ModelCodeExtractor()
        all_models = {}

        model_files = [
            'user/models/user_model.py',
            'userapp/models/userapp_model.py',
            # Add more model file paths here as needed
        ]

        for model_file in model_files:
            model_path = os.path.join(settings.BASE_DIR, model_file)
            if os.path.exists(model_path):
                with open(model_path, 'r') as file:
                    model_code = file.read()
                    extracted_classes = extractor.extract_model_code(model_code)
                    all_models[model_file] = {
                        class_name: class_code
                        for class_name, class_code in extracted_classes.items()
                        if class_name not in ignore_models
                    }

        with open(output_file, 'w') as f:
            f.write("# Combined Django Models\n\n")
            for file_path, models in all_models.items():
                f.write(f"# Models from {file_path}\n\n")
                for class_name, class_code in sorted(models.items()):
                    f.write(f"# Model: {class_name}\n")
                    f.write(class_code)
                    f.write("\n\n")

        self.stdout.write(self.style.SUCCESS(f'Successfully collected models into {output_file}'))