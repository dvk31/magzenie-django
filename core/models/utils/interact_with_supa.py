import os
import logging
import requests

SUPABASE_BASE_URL = "https://uzszwltfnidfbdbbemgw.supabase.co"
SUPABASE_AUTH_PATH = "/auth/v1"
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
logger = logging.getLogger(__name__)

def interact_with_supabase_auth(endpoint, data=None, method="POST", is_auth=True):
    # Determine the base URL path
    base_path = SUPABASE_AUTH_PATH if is_auth else ""
    # Adjusting for the login endpoint
    if endpoint == "token" and is_auth:
        url = f"{SUPABASE_BASE_URL}{base_path}/{endpoint}?grant_type=password"
    else:
        url = f"{SUPABASE_BASE_URL}{base_path}/{endpoint}"

    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Prefer": "return=representation"
    }

    response = requests.request(method, url, headers=headers, json=data)
    logger.info(f"Sent request to Supabase URL: {url} with data: {data}")

    try:
        return response.json()
    except Exception as e:
        logger.error(f"Error decoding JSON from Supabase response: {str(e)}")
        logger.error(f"Supabase response content: {response.text}")
        return {"error": {"message": "Invalid response from server."}}
