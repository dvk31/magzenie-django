# aiassistant/utils/twilio_webhook_utils.py
import logging
import os

from decouple import config
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

logger = logging.getLogger(__name__)


class TwilioWebhookUtility:
    def __init__(self):
        self.account_sid = config("TWILIO_ACCOUNT_SID")
        self.auth_token = config("TWILIO_AUTH_TOKEN")

    def send_sms(self, to_phone_number, from_phone_number, body):
        client = Client(self.account_sid, self.auth_token)
        message = client.messages.create(
            body=body, from_=from_phone_number, to=to_phone_number
        )
        return message

    def generate_twiml_response(self, message_body):
        response = MessagingResponse()
        response.message(message_body)
        return response.to_xml()

    def send_response(self, to_phone_number, from_phone_number, message_body):
        try:
            message = self.send_sms(to_phone_number, from_phone_number, message_body)
            logger.info(f"Sent response to {to_phone_number}: {message_body}")
            print(f"Sent response to {to_phone_number}: {message_body}")
            return message
        except Exception as e:
            logger.error(f"Error while sending response to {to_phone_number}: {e}")
            print(f"Error while sending response to {to_phone_number}: {e}")
            return None
