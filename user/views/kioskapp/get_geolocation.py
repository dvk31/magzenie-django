import requests
import logging

logger = logging.getLogger(__name__)

def get_geolocation(ip_address):
    try:
        response = requests.get(f'https://ipapi.co/{ip_address}/json/')
        data = response.json()
        
        if response.status_code == 200:
            return {
                'ip': ip_address,
                'country_code': data.get('country_code'),
                'country_name': data.get('country_name'),
                'city': data.get('city'),
                'postal_code': data.get('postal'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'time_zone': data.get('timezone'),
            }
        else:
            logger.warning(f"Failed to get geolocation for IP {ip_address}. Status code: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error occurred while getting geolocation for IP {ip_address}: {str(e)}")
        return None