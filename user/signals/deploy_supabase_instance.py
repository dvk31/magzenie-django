#singals/deploy_supabase_instance.py

import os
import requests
import json
from django.conf import settings

def deploy_supabase_instance(user_id):
    caprover_url = settings.CAPROVER_URL
    caprover_password = settings.CAPROVER_PASSWORD
    
    # Step 1: Authenticate with CapRover
    auth_response = requests.post(f"{caprover_url}/api/v2/login", json={
        "password": caprover_password
    })
    auth_token = auth_response.json()['data']['token']

    headers = {
        "x-captain-auth": auth_token,
        "Content-Type": "application/json"
    }

    # Step 2: Create a new app for the user's Supabase instance
    app_name = f"supabase-{user_id}"
    create_app_response = requests.post(f"{caprover_url}/api/v2/user/apps/appDefinitions/register", 
                                        headers=headers,
                                        json={"appName": app_name})

    # Step 3: Configure the app with Supabase
    supabase_config = {
        "instanceCount": 1,
        "notExposeAsWebApp": False,
        "containerHttpPort": "3000",
        "volumes": [
            {
                "volumeName": f"{app_name}-data",
                "containerPath": "/var/lib/postgresql/data"
            }
        ],
        "envVars": [
            {"key": "POSTGRES_PASSWORD", "value": os.urandom(24).hex()},
            {"key": "JWT_SECRET", "value": os.urandom(32).hex()},
            {"key": "ANON_KEY", "value": os.urandom(32).hex()},
            {"key": "SERVICE_ROLE_KEY", "value": os.urandom(32).hex()}
        ],
        "imageNameTag": "supabase/supabase:latest"
    }

    update_app_response = requests.post(f"{caprover_url}/api/v2/user/apps/appDefinitions/update", 
                                        headers=headers,
                                        json={"appName": app_name, "appDefinition": supabase_config})

    # Step 4: Get the app info to retrieve the URL
    app_info_response = requests.get(f"{caprover_url}/api/v2/user/apps/appDefinitions/{app_name}", 
                                     headers=headers)
    app_info = app_info_response.json()['data']
    instance_url = f"https://{app_info['customDomain']}"

    # Return the necessary information
    return {
        "project_ref": app_name,
        "project_id": app_name,
        "db_password": next(env['value'] for env in supabase_config['envVars'] if env['key'] == 'POSTGRES_PASSWORD'),
        "instance_url": instance_url,
        "api_key": next(env['value'] for env in supabase_config['envVars'] if env['key'] == 'SERVICE_ROLE_KEY'),
        "anon_key": next(env['value'] for env in supabase_config['envVars'] if env['key'] == 'ANON_KEY')
    }