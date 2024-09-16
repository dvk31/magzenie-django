# function_service.py

import logging
from db_connection import DatabaseConnection
from django.db import models

logger = logging.getLogger(__name__)

class DynamicFunction(models.Model):
    name = models.CharField(max_length=255)
    definition = models.TextField()
    schema = models.JSONField()
    supabase_function_name = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict)

class FunctionService:
    @staticmethod
    def create_dynamic_function(function_data):
        db_connection = DatabaseConnection()
        
        # Create the function in the database
        supabase_function_name = function_data['function_name'].lower()
        sql_definition = FunctionService.schema_to_sql(supabase_function_name, function_data['schema'])
        
        try:
            db_connection.execute_query(sql_definition)
            logger.info(f"Successfully created function: {supabase_function_name}")
        except Exception as e:
            logger.error(f"Failed to create function {supabase_function_name}: {str(e)}")
            raise

        # Create the DynamicFunction record
        dynamic_function = DynamicFunction.objects.create(
            name=function_data['function_name'],
            definition=function_data['definition'],
            schema=function_data['schema'],
            supabase_function_name=supabase_function_name,
            metadata=function_data.get('metadata', {})
        )
        
        return dynamic_function

    @staticmethod
    def delete_dynamic_function(dynamic_function):
        db_connection = DatabaseConnection()
        
        # Delete the function from the database
        delete_query = f"DROP FUNCTION IF EXISTS {dynamic_function.supabase_function_name};"
        
        try:
            db_connection.execute_query(delete_query)
            logger.info(f"Successfully deleted function: {dynamic_function.supabase_function_name}")
        except Exception as e:
            logger.error(f"Failed to delete function {dynamic_function.supabase_function_name}: {str(e)}")
            raise

        # Delete the DynamicFunction record
        dynamic_function.delete()

    @staticmethod
    def update_dynamic_function(dynamic_function, new_function_data):
        db_connection = DatabaseConnection()
        
        # Update the function in the database
        new_sql_definition = FunctionService.schema_to_sql(dynamic_function.supabase_function_name, new_function_data['schema'])
        
        try:
            db_connection.execute_query(new_sql_definition)
            logger.info(f"Successfully updated function: {dynamic_function.supabase_function_name}")
        except Exception as e:
            logger.error(f"Failed to update function {dynamic_function.supabase_function_name}: {str(e)}")
            raise

        # Update the DynamicFunction record
        dynamic_function.definition = new_function_data['definition']
        dynamic_function.schema = new_function_data['schema']
        dynamic_function.metadata = new_function_data.get('metadata', {})
        dynamic_function.save()

    @staticmethod
    def schema_to_sql(function_name, schema):
        params = ', '.join([f"{p['name']} {p['type']}" + (f" DEFAULT {p['default']}" if 'default' in p else '') for p in schema['parameters']])
        body = schema['definition'].split('AS $$')[1].split('$$;')[0].strip()
        
        sql = f"""
        CREATE OR REPLACE FUNCTION {function_name}({params})
        RETURNS {schema['return_type']}
        LANGUAGE plpgsql
        AS $$
        {body}
        $$;
        """
        return sql