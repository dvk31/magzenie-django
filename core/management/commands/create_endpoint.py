import requests
import logging
import traceback
from django.core.management.base import BaseCommand
from django.db import transaction
from webhook.models import Endpoint
import json

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch OpenAPI (Swagger) specification and populate Endpoint model'

    def add_arguments(self, parser):
        parser.add_argument('swagger_url', type=str, help='URL to the OpenAPI (Swagger) specification')

    def handle(self, *args, **kwargs):
        swagger_url = kwargs['swagger_url']
        logger.info(f'Fetching OpenAPI specification from {swagger_url}')
        
        try:
            swagger_data = self.fetch_swagger_data(swagger_url)
            self.populate_endpoints(swagger_data)
            self.stdout.write(self.style.SUCCESS('Successfully populated endpoints from OpenAPI specification'))
        except Exception as e:
            logger.error(f'Error occurred: {e}')
            logger.error(traceback.format_exc())
            self.stderr.write(self.style.ERROR(f'Error occurred: {e}'))

    def fetch_swagger_data(self, swagger_url):
        response = requests.get(swagger_url)
        if response.status_code != 200:
            raise Exception(f'Failed to fetch OpenAPI specification: {response.status_code}')
        return response.json()

    @transaction.atomic
    def populate_endpoints(self, swagger_data):
        host = swagger_data.get('host')
        base_path = swagger_data.get('basePath', '')
        schemes = swagger_data.get('schemes', ['https'])
        paths = swagger_data.get('paths', {})

        unexpected_structure_endpoints = []

        for path, methods in paths.items():
            for method, details in methods.items():
                try:
                    if not isinstance(details, dict):
                        logger.error(f'Unexpected structure in details for path {path} and method {method}: {details}')
                        unexpected_structure_endpoints.append((path, method, 'details'))
                        continue

                    base_url = f"{schemes[0]}://{host}{base_path}"
                    endpoint_url = path
                    operation_id = details.get('operationId', '')
                    description = details.get('description', '')
                    parameters = details.get('parameters', [])

                    if not isinstance(parameters, list):
                        logger.error(f'Unexpected structure in parameters for path {path} and method {method}: {parameters}')
                        unexpected_structure_endpoints.append((path, method, 'parameters'))
                        continue

                    # Skip endpoints with only path parameters
                    if parameters and all(isinstance(param, dict) and param.get('in') == 'path' for param in parameters):
                        logger.info(f"Skipping path parameters for endpoint {operation_id} ({method.upper()} {endpoint_url})")
                        continue

                    payload_structure = self.extract_payload_structure(parameters)
                    response_structure = self.extract_response_structure(details.get('responses', {}))

                    Endpoint.objects.update_or_create(
                        name=operation_id,
                        method=method.upper(),
                        defaults={
                            'base_url': base_url,
                            'url': endpoint_url,
                            'description': description,
                            'payload_structure': payload_structure,
                            'response_structure': response_structure,
                        }
                    )
                    logger.info(f'Populated endpoint: {operation_id} ({method.upper()} {endpoint_url})')
                except Exception as e:
                    logger.error(f'Error populating endpoint for path {path} and method {method}: {e}')
                    logger.error(traceback.format_exc())
                    raise

        if unexpected_structure_endpoints:
            logger.warning("Endpoints with unexpected structures:")
            for path, method, issue in unexpected_structure_endpoints:
                # Print the exact content of details for further debugging
                logger.warning(f"Path: {path}, Method: {method}, Issue: {issue}, Details: {json.dumps(swagger_data['paths'][path][method], indent=2)}")

    def extract_payload_structure(self, parameters):
        payload_structure = {'fields': []}
        for param in parameters:
            if param['in'] == 'body' and 'schema' in param:
                ref = param['schema'].get('$ref', '')
                if ref:
                    payload_structure['fields'].append({'name': ref.split('/')[-1], 'type': 'object'})
            elif param['in'] in ['query', 'path', 'header', 'formData']:
                payload_structure['fields'].append({
                    'name': param['name'],
                    'type': param['type'],
                    'required': param.get('required', False)
                })
        return payload_structure

    def extract_response_structure(self, responses):
        response_structure = {'fields': []}
        for status, response in responses.items():
            if 'schema' in response:
                ref = response['schema'].get('$ref', '')
                if ref:
                    response_structure['fields'].append({'name': ref.split('/')[-1], 'type': 'object'})
        return response_structure