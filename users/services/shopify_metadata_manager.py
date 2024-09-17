import logging
import json
import os
import traceback
from .shopify_connection import ShopifyConnectionManager

logger = logging.getLogger(__name__)

class ShopifyMetadataManager:
    def __init__(self, definitions_file='metaobject_definitions.json'):
        self.connection_manager = ShopifyConnectionManager()
        self.definitions_file = definitions_file
        self.metaobject_definitions = {}
        self.metafield_definitions = []

    def setup_metadata(self, force=False):
        logger.info(f"Starting metadata setup (Force update: {force})")
        try:
            with self.connection_manager:
                self._load_definitions()
                self._setup_metaobject_definitions(force)
                self._setup_metafields(force)
            logger.info("Metadata setup completed successfully")
        except Exception as e:
            logger.error(f"Error during metadata setup: {e}")
            logger.error(traceback.format_exc())
            raise

    def _load_definitions(self):
        logger.info(f"Loading definitions from {self.definitions_file}")
        if not os.path.exists(self.definitions_file):
            logger.error(f"Definitions file not found: {self.definitions_file}")
            raise FileNotFoundError(f"Definitions file not found: {self.definitions_file}")

        try:
            with open(self.definitions_file, 'r') as file:
                data = json.load(file)
                self.metaobject_definitions = {d['name']: d for d in data.get('metaobjects', [])}
                self.metafield_definitions = data.get('metafields', [])
            logger.info("Definitions loaded successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON in definitions file: {e}")
            raise

    def _get_creation_order(self):
        dependencies = {}
        for name, definition in self.metaobject_definitions.items():
            dependencies[name] = set()
            for field in definition['fields']:
                if field['type'] == 'metaobject_reference' or field['type'] == 'list.metaobject_reference':
                    if 'validations' in field:
                        for validation in field['validations']:
                            if validation['name'] == 'metaobject_definition':
                                dependencies[name].add(validation['value'])

        creation_order = []
        visited = set()

        def visit(name):
            if name in visited:
                return
            visited.add(name)
            for dep in dependencies[name]:
                visit(dep)
            creation_order.append(name)

        for name in dependencies:
            visit(name)

        return creation_order

    def _setup_metaobject_definitions(self, force=False):
        logger.info("Setting up metaobject definitions")
        creation_order = self._get_creation_order()
        created_definitions = set()

        # First pass: Create all metaobject definitions without references
        for name in creation_order:
            try:
                definition = self.metaobject_definitions[name]
                field_definitions = self._prepare_field_definitions(definition['fields'], created_definitions, include_references=False)
                self._create_or_update_metaobject_definition(
                    name=name,
                    field_definitions=field_definitions,
                    force=force
                )
                created_definitions.add(name)
            except Exception as e:
                logger.error(f"Error setting up metaobject definition '{name}': {e}")
                logger.error(traceback.format_exc())
                raise

        # Second pass: Update all definitions to include references
        for name in creation_order:
            try:
                definition = self.metaobject_definitions[name]
                field_definitions = self._prepare_field_definitions(definition['fields'], created_definitions, include_references=True)
                self._create_or_update_metaobject_definition(
                    name=name,
                    field_definitions=field_definitions,
                    force=True
                )
            except Exception as e:
                logger.error(f"Error updating metaobject definition '{name}': {e}")
                logger.error(traceback.format_exc())
                raise

    def _setup_metafields(self, force=False):
        logger.info("Setting up metafields")
        for metafield in self.metafield_definitions:
            try:
                self._create_or_update_metafields(
                    owner_resource=metafield['owner_resource'],
                    fields=metafield['fields'],
                    force=force
                )
            except Exception as e:
                logger.error(f"Error setting up metafields for {metafield['owner_resource']}: {e}")
                logger.error(traceback.format_exc())
                raise

    def _prepare_field_definitions(self, fields, created_definitions, include_references=False):
        prepared_fields = []
        for field in fields:
            field_def = {
                "name": field['name'],
                "key": field['key'],
                "type": field['type'],
            }
            
            if field['type'] in ['metaobject_reference', 'list.metaobject_reference'] and include_references:
                if 'validations' in field:
                    for validation in field['validations']:
                        if validation['name'] == 'metaobject_definition':
                            if validation['value'] in created_definitions:
                                metaobject_id = self._get_global_id(validation['value'])
                                if metaobject_id:
                                    field_def['validations'] = [{
                                        "name": "metaobject_definition",
                                        "value": metaobject_id
                                    }]
                                else:
                                    logger.warning(f"Metaobject definition '{validation['value']}' not found for field '{field['name']}'. Skipping this field.")
                                    continue
                            else:
                                logger.warning(f"Metaobject definition '{validation['value']}' not created yet for field '{field['name']}'. Skipping this field.")
                                continue
            
            prepared_fields.append(field_def)
        
        logger.debug(f"Prepared field definitions: {prepared_fields}")
        return prepared_fields

    def _get_global_id(self, name):
        existing_definition = self.connection_manager.get_metaobject_definition(name)
        if existing_definition:
            return existing_definition['id']
        return None


    def _get_validations(self, field, created_definitions):
        validations = []
        if field['type'] == 'metaobject_reference' or field['type'] == 'list.metaobject_reference':
            if 'validations' in field:
                for validation in field['validations']:
                    if validation['name'] == 'metaobject_definition':
                        if validation['value'] in created_definitions:
                            validations.append(validation)
        return validations

   


    def _metaobject_exists(self, validations):
        for validation in validations:
            if validation['name'] == 'metaobject_definition':
                return self.connection_manager.get_metaobject_definition(self._get_global_id(validation['value'])) is not None
        return True



    def _create_or_update_metaobject_definition(self, name, field_definitions, force=False):
        try:
            existing_definition = self.connection_manager.get_metaobject_definition(name)
            
            if existing_definition:
                if force:
                    logger.info(f"Updating metaobject definition '{name}'")
                    logger.debug(f"Field definitions for update: {field_definitions}")
                    self.connection_manager.update_metaobject_definition(
                        existing_definition['id'],
                        name,
                        field_definitions
                    )
                else:
                    logger.info(f"Metaobject definition '{name}' already exists. Use force=True to update.")
                return

            logger.info(f"Creating new metaobject definition '{name}'")
            logger.debug(f"Field definitions for creation: {field_definitions}")
            result = self.connection_manager.create_metaobject_definition(
                name,
                f"{name}_type",  # Use a unique type name
                field_definitions
            )
            logger.info(f"Metaobject definition '{name}' created successfully: {result}")
        except Exception as e:
            logger.error(f"Error processing metaobject definition '{name}': {e}")
            logger.error(traceback.format_exc())
            raise

    def _create_or_update_metaobject_definition(self, name, field_definitions, force=False):
        try:
            existing_definition = self.connection_manager.get_metaobject_definition(name)
            
            if existing_definition:
                if force:
                    logger.info(f"Updating metaobject definition '{name}'")
                    logger.debug(f"Field definitions for update: {field_definitions}")
                    result = self.connection_manager.update_metaobject_definition(
                        existing_definition['id'],
                        name,
                        field_definitions
                    )
                    logger.info(f"Metaobject definition '{name}' updated successfully: {result}")
                else:
                    logger.info(f"Metaobject definition '{name}' already exists. Use force=True to update.")
                return

            logger.info(f"Creating new metaobject definition '{name}'")
            logger.debug(f"Field definitions for creation: {field_definitions}")
            result = self.connection_manager.create_metaobject_definition(
                name,
                f"{name}_type",  # Use a unique type name
                field_definitions
            )
            logger.info(f"Metaobject definition '{name}' created successfully: {result}")
        except Exception as e:
            logger.error(f"Error processing metaobject definition '{name}': {e}")
            logger.error(f"Field definitions: {field_definitions}")
            logger.error(traceback.format_exc())
            raise