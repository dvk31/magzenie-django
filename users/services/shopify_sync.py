#user/services/shopify_sync.py

from django.db import models
from django.conf import settings
import json
from .shopify_connection import ShopifyConnectionManager

class ShopifySync:
    @classmethod
    def sync_from_shopify(cls):
        raise NotImplementedError("Subclasses must implement sync_from_shopify method")

    @staticmethod
    def graphql_query(query, variables=None):
        with ShopifyConnectionManager() as manager:
            response = requests.post(
                manager.admin_url,
                json={"query": query, "variables": variables},
                headers=manager.admin_headers
            )
            response.raise_for_status()
            return response.json()['data']

    @classmethod
    def create_metaobject(cls, type, fields):
        query = """
        mutation metaobjectCreate($metaobject: MetaobjectCreateInput!) {
          metaobjectCreate(metaobject: $metaobject) {
            metaobject {
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
            "metaobject": {
                "type": type,
                "fields": [{"key": key, "value": value} for key, value in fields.items()]
            }
        }
        result = cls.graphql_query(query, variables)
        if result['metaobjectCreate']['userErrors']:
            raise Exception(f"Error creating metaobject: {result['metaobjectCreate']['userErrors']}")
        return result['metaobjectCreate']['metaobject']['id']

    @classmethod
    def update_metaobject(cls, id, fields):
        query = """
        mutation metaobjectUpdate($id: ID!, $metaobject: MetaobjectUpdateInput!) {
          metaobjectUpdate(id: $id, metaobject: $metaobject) {
            metaobject {
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
            "id": id,
            "metaobject": {
                "fields": [{"key": key, "value": value} for key, value in fields.items()]
            }
        }
        result = cls.graphql_query(query, variables)
        if result['metaobjectUpdate']['userErrors']:
            raise Exception(f"Error updating metaobject: {result['metaobjectUpdate']['userErrors']}")
        return result['metaobjectUpdate']['metaobject']['id']

    @classmethod
    def create_or_update_metafield(cls, owner_id, owner_type, namespace, key, type, value):
        query = """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) {
            metafields {
              id
              key
              namespace
              value
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "metafields": [
                {
                    "ownerId": owner_id,
                    "namespace": namespace,
                    "key": key,
                    "type": type,
                    "value": json.dumps(value) if type == "json" else str(value)
                }
            ]
        }
        result = cls.graphql_query(query, variables)
        if result['metafieldsSet']['userErrors']:
            raise Exception(f"Error setting metafield: {result['metafieldsSet']['userErrors']}")
        return result['metafieldsSet']['metafields'][0]['id']

