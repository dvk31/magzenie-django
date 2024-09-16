#django/user/services/get_content_url.py

from .shopify_connection import ShopifyConnectionManager

import logging

logger = logging.getLogger(__name__)

def get_shopify_video_url(product_id):
    """
    Retrieves the video URL of a specific product from Shopify using its ID.

    :param product_id: The ID of the product whose video URL is to be retrieved.
    :return: The video URL if found, otherwise None.
    """
    # First, get the video GID from the product's metafields
    query = """
    query getProductVideoGid($id: ID!) {
      product(id: $id) {
        metafields(first: 10) {
          edges {
            node {
              namespace
              key
              value
            }
          }
        }
      }
    }
    """
    variables = {"id": product_id}

    with ShopifyConnectionManager() as manager:
        result = manager.execute_graphql_query(query, variables)

    video_gid = None
    if result and 'data' in result:
        metafields = result['data']['product']['metafields']['edges']
        for metafield in metafields:
            node = metafield['node']
            if node['key'] == 'kiosk_video':  # Adjust this key to match your setup
                video_gid = node['value']
                break

    if not video_gid:
        return None

    # Now, use the video GID to get the actual video URL
    video_query = """
    query getVideoUrl($id: ID!) {
      node(id: $id) {
        ... on Video {
          sources {
            url
          }
        }
      }
    }
    """
    video_variables = {"id": video_gid}

    with ShopifyConnectionManager() as manager:
        video_result = manager.execute_graphql_query(video_query, video_variables)

    if video_result and 'data' in video_result:
        node = video_result['data'].get('node')
        if node and 'sources' in node:
            sources = node['sources']
            if sources:
                return sources[0]['url']  # Assuming you want the first available source URL

    return None





def get_shopify_thumbnail_url(product_id):
    with ShopifyConnectionManager() as scm:
        query = """
        query getProductThumbnail($id: ID!) {
          product(id: $id) {
            featuredImage {
              url
            }
          }
        }
        """
        # Ensure the product_id is correctly formatted
        variables = {"id": product_id}
        
        result = scm.execute_graphql_query(query, variables)
        
        if result and 'data' in result:
            product = result['data']['product']
            if product and product['featuredImage']:
                return product['featuredImage']['url']
        
        logger.error(f"Failed to retrieve thumbnail URL for product ID: {product_id}")
        return None

#/user/services/get_content_url.py
import uuid
from django.conf import settings

def generate_qr_code_filename(kiosk_id, product_id):
    return f"qr_code_{kiosk_id}_{product_id}.png"

def predict_qr_code_url(filename):
    shop_id = "1/0887/4455/8865"  # Updated to match the actual Shopify URL structure
    return f"https://cdn.shopify.com/s/files/{shop_id}/files/{filename}"

def get_qr_code_image_url(kiosk_id, product_id):
    filename = generate_qr_code_filename(kiosk_id, product_id)
    return predict_qr_code_url(filename)