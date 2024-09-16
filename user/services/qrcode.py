# django/user/services/qrcode.py

import qrcode
import io
from django.conf import settings
import logging
from urllib.parse import urljoin, quote

logger = logging.getLogger(__name__)

def generate_qr_code(relative_url, domain=None):
    """
    Generate a QR code for a given relative URL.
    
    :param relative_url: The relative URL to encode in the QR code
    :param domain: Optional domain to prepend to the relative URL. If not provided, uses FRONTEND_URL from settings.
    :return: BytesIO object containing the QR code image
    """
    try:
        if domain is None:
            domain = getattr(settings, 'FRONTEND_URL', 'https://defaultdomain.com')
        
        full_url = urljoin(domain, relative_url)
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(full_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    except Exception as e:
        logger.error(f"Error generating QR code for URL {full_url}: {str(e)}")
        logger.exception("Traceback:")
        raise


def ensure_gid(id_value, type):
    """
    Ensure the ID is in the GID format.
    If it's not, convert it to the GID format.
    """
    if isinstance(id_value, str) and id_value.startswith('gid://'):
        return id_value
    return f'gid://shopify/{type}/{id_value}'

def get_qr_code_relative_url(kiosk_shopify_id, product_shopify_id):
    """
    Generate the relative URL for a kiosk-product QR code using Shopify IDs.
    
    :param kiosk_shopify_id: The Shopify ID of the kiosk metaobject
    :param product_shopify_id: The Shopify ID of the product
    :return: Relative URL string
    """
    kiosk_gid = ensure_gid(kiosk_shopify_id, 'Metaobject')
    product_gid = ensure_gid(product_shopify_id, 'Product')
    
    # Encode the GIDs to make them URL-safe
    encoded_kiosk_gid = quote(kiosk_gid)
    encoded_product_gid = quote(product_gid)
    
    return f"/result/{encoded_kiosk_gid}/{encoded_product_gid}"