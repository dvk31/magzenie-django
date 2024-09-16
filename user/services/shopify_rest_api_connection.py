import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth


class ShopifyResApiConnectionManager:
    def __init__(self):
        self.shop_url = settings.SHOPIFY_STORE_URL
        self.api_version = settings.SHOPIFY_API_VERSION
        self.access_token = settings.SHOPIFY_ADMIN_ACCESS_TOKEN
        self.base_url = f"https://{self.shop_url}/admin/api/{self.api_version}"

    def _make_request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Shopify-Access-Token': self.access_token
        }
        
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            del kwargs['headers']
        
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def get(self, endpoint, **kwargs):
        return self._make_request('GET', endpoint, **kwargs)

    def post(self, endpoint, **kwargs):
        return self._make_request('POST', endpoint, **kwargs)

    def put(self, endpoint, **kwargs):
        return self._make_request('PUT', endpoint, **kwargs)

    def delete(self, endpoint, **kwargs):
        return self._make_request('DELETE', endpoint, **kwargs)

    def create_metaobject_definition(self, definition):
        endpoint = '/metaobjects/definitions.json'
        data = {'definition': definition}
        return self.post(endpoint, json=data)

    def create_metafield(self, owner_resource, owner_id, metafield):
        endpoint = f'/{owner_resource}/{owner_id}/metafields.json'
        data = {'metafield': metafield}
        return self.post(endpoint, json=data)