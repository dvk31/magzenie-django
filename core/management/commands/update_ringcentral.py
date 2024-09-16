import os
from django.core.management.base import BaseCommand
from ringcentral import SDK

class Command(BaseCommand):
    help = 'Updates the RingCentral subscription webhook URL and lists all active subscriptions'

    def handle(self, *args, **options):
        # Initialize the SDK and login
        rcsdk = SDK(os.environ['RINGCENTRAL_CLIENT_ID'], 
                    os.environ['RINGCENTRAL_CLIENT_SECRET'], 
                    os.environ['RINGCENTRAL_SERVER_URL'])
        platform = rcsdk.platform()
        platform.login(jwt=os.environ['RINGCENTRAL_JWT_TOKEN'])

        # Define the webhook URL
        new_webhook_url = 'https://dev.withgpt.com/api/v1/realtime-webhook/'

        # Retrieve the existing subscription
        try:
            response = platform.get('/restapi/v1.0/subscription')
            subscriptions_data = response.json()
            
            # Ensure that we are accessing the 'records' correctly
            if hasattr(subscriptions_data, 'records') and isinstance(subscriptions_data.records, list):
                subscriptions = subscriptions_data.records
            else:
                self.stdout.write("No subscriptions found. Creating a new one.")
                # Create a new subscription
                create_response = platform.post('/restapi/v1.0/subscription', {
                    'eventFilters': ['/restapi/v1.0/account/~/extension/~/message-store'],
                    'deliveryMode': {
                        'transportType': 'WebHook',
                        'address': new_webhook_url
                    },
                    'expiresIn': 500000
                })
                self.stdout.write("Subscription created successfully: " + str(create_response.json()))
                return

            # Update the first subscription found
            subscription_id = subscriptions[0].id  # Accessing id directly
            update_response = platform.put(f'/restapi/v1.0/subscription/{subscription_id}', {
                'deliveryMode': {
                    'transportType': 'WebHook',
                    'address': new_webhook_url
                }
            })
            self.stdout.write("Subscription updated successfully: " + str(update_response.json()))
        except Exception as e:
            self.stdout.write("Error handling subscription: " + str(e))