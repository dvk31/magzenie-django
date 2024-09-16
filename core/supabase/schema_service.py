
# schema_service.py

import logging
from django.conf import settings
from django.apps import apps
from .db_connect import DatabaseConnection
logger = logging.getLogger(__name__)





logger = logging.getLogger(__name__)

class SchemaService:
    @staticmethod
    def get_app_models(app_labels):
        app_models = []
        for app_label in app_labels:
            try:
                app_config = apps.get_app_config(app_label)
                app_models.extend(app_config.get_models())
            except LookupError:
                logger.warning(f"App '{app_label}' not found.")
        return app_models

    @staticmethod
    def get_tables(app_models):
        table_names = [model._meta.db_table for model in app_models]
        placeholders = ', '.join(['%s'] * len(table_names))
        query = f"""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name IN ({placeholders});
        """
        return DatabaseConnection.execute_query(query, table_names)

    @staticmethod
    def get_table_columns(table_name):
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
        """
        return DatabaseConnection.execute_query(query, [table_name])


    @staticmethod
    def get_functions(app_labels):
        function_prefixes = [f"{app_label}_" for app_label in app_labels]
        placeholders = ', '.join(['%s'] * len(function_prefixes))
        query = f"""
        SELECT routines.routine_name, 
            routines.data_type AS return_type,
            parameters.parameter_name,
            parameters.data_type AS parameter_type,
            parameters.parameter_mode
        FROM information_schema.routines
        LEFT JOIN information_schema.parameters ON 
            routines.specific_name = parameters.specific_name
        WHERE routines.specific_schema = 'public'
        AND routines.routine_type = 'FUNCTION'
        AND ({' OR '.join([f"routines.routine_name LIKE %s || '%%'" for _ in function_prefixes])})
        ORDER BY routines.routine_name, parameters.ordinal_position;
        """
        return DatabaseConnection.execute_query(query, function_prefixes)

    @staticmethod
    def get_function_definition(function_name):
        query = """
        SELECT pg_get_functiondef(p.oid) as function_def
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = %s;
        """
        return DatabaseConnection.execute_query(query, [function_name])


    @classmethod
    def get_schema(cls):
        # Get the app labels from settings
        our_apps = [
            'core', 'user', 'store', 'merchant', 'customer'
        ]
        
        app_models = cls.get_app_models(our_apps)
        
        schema = {
            'tables': {},
            'functions': {}
        }

        # Get tables
        tables = cls.get_tables(app_models)
        for table in tables:
            table_name = table['table_name']
            columns = cls.get_table_columns(table_name)
            schema['tables'][table_name] = columns

        # Get functions
        functions = cls.get_functions(our_apps)
        if functions:
            for func in functions:
                func_name = func['routine_name']
                if func_name not in schema['functions']:
                    schema['functions'][func_name] = {
                        'return_type': func['return_type'],
                        'parameters': [],
                        'definition': None
                    }
                if func['parameter_name']:
                    schema['functions'][func_name]['parameters'].append({
                        'name': func['parameter_name'],
                        'type': func['parameter_type'],
                        'mode': func['parameter_mode']
                    })

            # Get function definitions
            for func_name in schema['functions']:
                definition = cls.get_function_definition(func_name)
                if definition:
                    schema['functions'][func_name]['definition'] = definition[0]['function_def']

        return schema