# user/services/update_metafield.py

   def update_metafield(manager, owner_id, namespace, key, value_type, value):
       mutation = """
       mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
           metafieldsSet(metafields: $metafields) {
               metafields {
                   id
                   key
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
           "metafields": [{
               "ownerId": owner_id,
               "namespace": namespace,
               "key": key,
               "type": value_type,
               "value": value
           }]
       }
       return execute_graphql(manager, mutation, variables)