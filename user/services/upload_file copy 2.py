import requests
from xml.etree import ElementTree as ET
import logging
import traceback

logger = logging.getLogger(__name__)

def upload_file_to_shopify(file_content, filename, file_type, product_id, manager):
    """
    Uploads a file to Shopify and returns the file ID and URL.
    
    :param file_content: The content of the file to upload (bytes)
    :param filename: The name of the file
    :param file_type: The MIME type of the file (e.g., 'image/png')
    :param product_id: The ID of the product associated with the file
    :param manager: An instance of ShopifyConnectionManager
    :return: A tuple (file_id, file_url) if successful, (None, None) otherwise
    """
    try:
        # Step 1: Create a staged upload
        staged_upload_mutation = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
          stagedUploadsCreate(input: $input) {
            stagedTargets {
              resourceUrl
              url
              parameters {
                name
                value
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        file_size_str = str(len(file_content))
        staged_upload_variables = {
            "input": [{
                "resource": "FILE",
                "filename": filename,
                "mimeType": file_type,
                "fileSize": file_size_str,
                "httpMethod": "POST"
            }]
        }

        staged_upload_result = manager.execute_graphql_query(staged_upload_mutation, staged_upload_variables)
        if 'errors' in staged_upload_result or not staged_upload_result.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets'):
            logger.error(f"Failed to create staged upload URL: {staged_upload_result}")
            return None, None

        staged_target = staged_upload_result['data']['stagedUploadsCreate']['stagedTargets'][0]
        upload_url = staged_target['url']
        upload_params = staged_target['parameters']

        # Step 2: Upload the file to the staged URL
        files = {'file': (filename, file_content, file_type)}
        response = requests.post(upload_url, data={param['name']: param['value'] for param in upload_params}, files=files)

        if response.status_code != 201:
            logger.error(f"Failed to upload file to staged URL. Status code: {response.status_code}, Content: {response.content}")
            return None, None

        # Parse XML response to get the Location URL
        try:
            root = ET.fromstring(response.content)
            location_url = root.find('Location').text
        except Exception as e:
            logger.error(f"Failed to parse XML response: {str(e)}")
            logger.error(f"Response content: {response.content}")
            return None, None

        # Step 3: Create the file in Shopify
        file_create_mutation = """
        mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files {
              ... on MediaImage {
                id
                image {
                  url
                }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        file_create_variables = {
            "files": [{
                "alt": f"File for product {product_id}",
                "contentType": file_type.split('/')[0].upper(),
                "originalSource": location_url
            }]
        }

        file_create_result = manager.execute_graphql_query(file_create_mutation, file_create_variables)
        
        logger.info(f"File create result: {file_create_result}")  # Add this line for debugging
        
        if file_create_result is None:
            logger.error("File create result is None")
            return None, None

        if file_create_result.get('data', {}).get('fileCreate', {}).get('files'):
            file = file_create_result['data']['fileCreate']['files'][0]
            file_id = file['id']
            file_url = file['image']['url']
            logger.info(f"Successfully uploaded file for product {product_id}")
            return file_id, file_url
        else:
            error_message = file_create_result.get('data', {}).get('fileCreate', {}).get('userErrors', [])
            logger.error(f"Failed to create file in Shopify for product {product_id}: {error_message}")
            return None, None

    except Exception as e:
        logger.error(f"Error uploading file for product {product_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return None, None