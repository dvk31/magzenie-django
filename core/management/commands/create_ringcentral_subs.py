import os
from django.core.management.base import BaseCommand
from ringcentral import SDK
from dotenv import load_dotenv

class Command(BaseCommand):
    help = 'Create a RingCentral webhook subscription'

    def handle(self, *args, **kwargs):
        load_dotenv()  # Load environment variables from .env file

        # Initialize the RingCentral SDK
        rcsdk = SDK(os.environ['RINGCENTRAL_CLIENT_ID'], os.environ['RINGCENTRAL_CLIENT_SECRET'], os.environ['RINGCENTRAL_SERVER_URL'])
        platform = rcsdk.platform()

        # Log in to the RingCentral platform
        try:
            platform.login(jwt=os.environ['RINGCENTRAL_JWT_TOKEN'])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error logging in: {str(e)}'))
            return

        # Define the event filters
        event_filters = [
            '/restapi/v1.0/account/~/extension/~/telephony/sessions',
            '/restapi/v1.0/account/~/extension/~/presence?detailedTelephonyState=true'
        ]

        # Set the webhook notification URL
        notification_url = 'https://dev.withgpt.com/api/v1/realtime-webhook/'

        # Create the subscription
        try:
            subscription_response = platform.post('/restapi/v1.0/subscription', {
                'eventFilters': event_filters,
                'deliveryMode': {
                    'transportType': 'WebHook',
                    'address': notification_url
                }
            })
            self.stdout.write(self.style.SUCCESS(f'Subscription created: {subscription_response.json()}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating subscription: {str(e)}'))
            if hasattr(e, 'response') and e.response is not None:
                self.stdout.write(self.style.ERROR(f'Status Code: {e.response.status_code}'))
                self.stdout.write(self.style.ERROR(f'Response Text: {e.response.text}'))
