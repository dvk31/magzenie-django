 def admin_graphql_call(self, query, variables=None):
        try:
            logger.debug(f"Sending GraphQL query: {query} with variables: {variables}")
            response = requests.post(
                self.admin_url,
                json={"query": query, "variables": variables},
                headers=self.admin_headers
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"GraphQL API response: {data}")
            if "errors" in data:
                raise Exception(f"GraphQL errors: {data['errors']}")
            return data["data"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error in GraphQL API call: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in GraphQL API call: {str(e)}")
            raise

    def get_metaobject_definition(self, name):
        query = """
        query getMetaobjectDefinition($name: String!) {
        metaobjectDefinitions(first: 1, query: $name) {
            edges {
            node {
                id
                name
                type
            }
            }
        }
        }
        """
        variables = {"name": name}
        result = self.admin_graphql_call(query, variables)
        definitions = result.get('data', {}).get('metaobjectDefinitions', {}).get('edges', [])
        return definitions[0]['node'] if definitions else None

    def create_metaobject_definition(self, name, type, field_definitions):
        mutation = """
        mutation createMetaobjectDefinition($definition: MetaobjectDefinitionCreateInput!) {
        metaobjectDefinitionCreate(definition: $definition) {
            metaobjectDefinition {
            id
            name
            type
            }
            userErrors {
            field
            message
            }
        }
        }
        """
        definition_data = {
            "name": name,
            "type": type,
            "fieldDefinitions": [
                {
                    "name": field['name'],
                    "key": field['key'],
                    "type": field['type'],
                }
                for field in field_definitions
            ]
        }
        variables = {"definition": definition_data}
        try:
            result = self.admin_graphql_call(mutation, variables)
            logger.debug(f"API response for creating metaobject definition: {result}")
            if 'userErrors' in result['metaobjectDefinitionCreate'] and result['metaobjectDefinitionCreate']['userErrors']:
                raise Exception(f"User errors: {result['metaobjectDefinitionCreate']['userErrors']}")
            if 'metaobjectDefinition' not in result['metaobjectDefinitionCreate'] or not result['metaobjectDefinitionCreate']['metaobjectDefinition']:
                raise Exception(f"Failed to create metaobject definition. API response: {result}")
            return result['metaobjectDefinitionCreate']['metaobjectDefinition']
        except Exception as e:
            logger.error(f"Error creating metaobject definition: {str(e)}")
            raise

    def update_metaobject_definition(self, id, name, field_definitions):
        mutation = """
        mutation metaobjectDefinitionUpdate($id: ID!, $definition: MetaobjectDefinitionUpdateInput!) {
        metaobjectDefinitionUpdate(id: $id, definition: $definition) {
            metaobjectDefinition {
            id
            name
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
            "definition": {
                "name": name,
                "fieldDefinitions": field_definitions
            }
        }
        result = self.admin_graphql_call(mutation, variables)
        return result

    def get_metafield(self, owner_resource, key):
        query = """
        query getMetafield($owner_resource: MetafieldOwnerType!, $key: String!) {
          metafields(first: 1, ownerType: $owner_resource, keys: [$key]) {
            edges {
              node {
                id
                key
                type
              }
            }
          }
        }
        """
        variables = {"owner_resource": owner_resource.upper(), "key": key}
        try:
            result = self.admin_graphql_call(query, variables)
            metafields = result.get('metafields', {}).get('edges', [])
            return metafields[0]['node'] if metafields else None
        except Exception as e:
            logger.error(f"Error fetching metafield: {str(e)}")
            return None

    def create_metafield(self, key, type, owner_resource):
        mutation = """
        mutation createMetafield($input: MetafieldsSetInput!) {
          metafieldsSet(metafields: [$input]) {
            metafields {
              id
              key
              type
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        input_data = {
            "key": key,
            "type": type,
            "ownerType": owner_resource.upper()
        }
        variables = {"input": input_data}
        try:
            result = self.admin_graphql_call(mutation, variables)
            if 'userErrors' in result['metafieldsSet']:
                raise Exception(f"User errors: {result['userErrors']}")
            return result['metafieldsSet']['metafields'][0]
        except Exception as e:
            logger.error(f"Error creating metafield: {str(e)}")
            raise

    def update_metafield(self, id, key, type, owner_resource):
        mutation = """
        mutation updateMetafield($input: MetafieldInput!) {
          metafieldUpdate(input: $input) {
            metafield {
              id
              key
              type
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        input_data = {
            "id": id,
            "key": key,
            "type": type,
            "ownerType": owner_resource.upper()
        }
        variables = {"input": input_data}
        try:
            result = self.admin_graphql_call(mutation, variables)
            if 'userErrors' in result['metafieldUpdate']:
                raise Exception(f"User errors: {result['userErrors']}")
            return result['metafieldUpdate']['metafield']
        except Exception as e:
            logger.error(f"Error updating metafield: {str(e)}")
            raise