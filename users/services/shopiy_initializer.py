from .shopify_connection import ShopifyConnectionManager
import requests
import json

class ShopifyInitializer:
    def __init__(self):
        self.connection_manager = ShopifyConnectionManager()

    def graphql_query(self, query, variables=None):
        with self.connection_manager as manager:
            response = requests.post(
                manager.admin_url,
                json={"query": query, "variables": variables},
                headers=manager.admin_headers
            )
            response.raise_for_status()
            return response.json()['data']

    def create_metaobject_definition(self, type, name, field_definitions):
        query = """
        mutation createMetaobjectDefinition($definition: MetaobjectDefinitionInput!) {
          metaobjectDefinitionCreate(definition: $definition) {
            metaobjectDefinition {
              id
              type
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "definition": {
                "type": type,
                "name": name,
                "fieldDefinitions": field_definitions
            }
        }
        result = self.graphql_query(query, variables)
        if result['metaobjectDefinitionCreate']['userErrors']:
            raise Exception(f"Error creating metaobject definition: {result['metaobjectDefinitionCreate']['userErrors']}")
        return result['metaobjectDefinitionCreate']['metaobjectDefinition']['id']

    def create_metafield_definition(self, owner_type, namespace, key, name, type):
        query = """
        mutation createMetafieldDefinition($definition: MetafieldDefinitionInput!) {
          metafieldDefinitionCreate(definition: $definition) {
            metafieldDefinition {
              id
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "definition": {
                "ownerType": owner_type,
                "namespace": namespace,
                "key": key,
                "name": name,
                "type": type
            }
        }
        result = self.graphql_query(query, variables)
        if result['metafieldDefinitionCreate']['userErrors']:
            raise Exception(f"Error creating metafield definition: {result['metafieldDefinitionCreate']['userErrors']}")
        return result['metafieldDefinitionCreate']['metafieldDefinition']['id']

    def initialize_shopify(self):
        # Create metaobject definitions
        self.create_metaobject_definition(
            "partner_store",
            "Partner Store",
            [
                {"key": "name", "name": "Name", "type": "single_line_text_field"},
                {"key": "owner", "name": "Owner", "type": "single_line_text_field"},
                {"key": "store_url", "name": "Store URL", "type": "url"},
            ]
        )

        self.create_metaobject_definition(
            "virtual_location",
            "Virtual Location",
            [
                {"key": "name", "name": "Name", "type": "single_line_text_field"},
                {"key": "address", "name": "Address", "type": "multi_line_text_field"},
                {"key": "partner_store", "name": "Partner Store", "type": "metaobject_reference", "validations": {"metaobject_definition": "partner_store"}},
                {"key": "is_kiosk", "name": "Is Kiosk", "type": "boolean"},
            ]
        )

        self.create_metaobject_definition(
            "kiosk",
            "Kiosk",
            [
                {"key": "name", "name": "Name", "type": "single_line_text_field"},
                {"key": "partner_store", "name": "Partner Store", "type": "metaobject_reference", "validations": {"metaobject_definition": "partner_store"}},
                {"key": "virtual_location", "name": "Virtual Location", "type": "metaobject_reference", "validations": {"metaobject_definition": "virtual_location"}},
                {"key": "location_within_store", "name": "Location Within Store", "type": "single_line_text_field"},
                {"key": "main_qr_code_url", "name": "Main QR Code URL", "type": "url"},
            ]
        )

        self.create_metaobject_definition(
            "kiosk_video",
            "Kiosk Video",
            [
                {"key": "title", "name": "Title", "type": "single_line_text_field"},
                {"key": "video_content_url", "name": "Video Content URL", "type": "url"},
                {"key": "product", "name": "Product", "type": "product_reference"},
                {"key": "kiosk", "name": "Kiosk", "type": "metaobject_reference", "validations": {"metaobject_definition": "kiosk"}},
                {"key": "is_active", "name": "Is Active", "type": "boolean"},
                {"key": "qr_code_url", "name": "QR Code URL", "type": "url"},
                {"key": "custom_page_url", "name": "Custom Page URL", "type": "url"},
            ]
        )

        self.create_metaobject_definition(
            "location_inventory",
            "Location Inventory",
            [
                {"key": "virtual_location", "name": "Virtual Location", "type": "metaobject_reference", "validations": {"metaobject_definition": "virtual_location"}},
                {"key": "product", "name": "Product", "type": "product_reference"},
                {"key": "available_quantity", "name": "Available Quantity", "type": "number_integer"},
                {"key": "reserved_quantity", "name": "Reserved Quantity", "type": "number_integer"},
                {"key": "last_updated", "name": "Last Updated", "type": "date_time"},
            ]
        )

        # Create metafield definitions
        self.create_metafield_definition(
            "PRODUCT",
            "global",
            "kiosk_ids",
            "Kiosk IDs",
            "list.single_line_text_field"
        )

        self.create_metafield_definition(
            "CUSTOMER",
            "global",
            "roles",
            "Roles",
            "list.single_line_text_field"
        )

        self.create_metafield_definition(
            "CUSTOMER",
            "global",
            "partner_store_id",
            "Partner Store ID",
            "single_line_text_field"
        )

        print("Shopify initialization complete.")

