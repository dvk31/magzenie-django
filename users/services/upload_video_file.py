import os
import requests
import json
import logging

logger = logging.getLogger(__name__)

def upload_video_file(manager, file_path):
    try:
        with open(file_path, 'rb') as file:
            file_content = file.read()
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
        stage_query = """
        mutation {
          stagedUploadsCreate(input: {
            resource: VIDEO,
            filename: "%s",
            mimeType: "video/mp4",
            httpMethod: POST,
            fileSize: "%d"
          }) {
            stagedTargets {
              url
              resourceUrl
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
        """ % (file_name, file_size)

        stage_result = manager.execute_graphql_query(stage_query)
        
        logger.debug(f"Stage result: {json.dumps(stage_result, indent=2)}")
        
        if 'errors' in stage_result:
            logger.error(f"GraphQL errors: {json.dumps(stage_result['errors'], indent=2)}")
            return False

        staged_targets = stage_result['data']['stagedUploadsCreate']['stagedTargets']
        if not staged_targets:
            logger.warning("No staged targets returned")
            return False

        staged_target = staged_targets[0]
        upload_url = staged_target['url']
        resource_url = staged_target['resourceUrl']

        # Perform the actual upload
        upload_params = {param['name']: param['value'] for param in staged_target['parameters']}
        files = {'file': (file_name, file_content)}

        logger.info(f"Uploading to URL: {upload_url}")
        logger.debug(f"Upload parameters: {json.dumps(upload_params, indent=2)}")

        response = requests.post(upload_url, data=upload_params, files=files)

        logger.info(f"Upload response status code: {response.status_code}")
        logger.debug(f"Upload response content: {response.text}")

        if response.status_code not in [200, 201, 204]:
            logger.error(f"Failed to upload video. Status code: {response.status_code}")
            return False

        # After successful upload, use fileCreate with the correct structure
        create_file_query = """
        mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files {
              id
              createdAt
              fileStatus
              preview {
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
        
        variables = {
            "files": [{
                "originalSource": resource_url,
                "alt": file_name,
                "contentType": "VIDEO"
            }]
        }

        create_result = manager.execute_graphql_query(create_file_query, variables)
        
        logger.debug(f"Create file result: {json.dumps(create_result, indent=2)}")

        if create_result and 'data' in create_result and 'fileCreate' in create_result['data']:
            if create_result['data']['fileCreate'].get('files'):
                created_file = create_result['data']['fileCreate']['files'][0]
                logger.info(f"Successfully created file: {created_file['id']}")
                logger.info(f"File status: {created_file['fileStatus']}")
                if created_file.get('preview') and created_file['preview'].get('image'):
                    logger.info(f"Preview URL: {created_file['preview']['image']['url']}")
                return True
            elif create_result['data']['fileCreate'].get('userErrors'):
                logger.error(f"User errors: {create_result['data']['fileCreate']['userErrors']}")
                return False
        else:
            logger.error("Failed to create file record")
            if 'errors' in create_result:
                logger.error(f"GraphQL errors: {create_result['errors']}")
            return False

    except Exception as e:
        logger.exception(f"Error uploading video: {str(e)}")
        return False