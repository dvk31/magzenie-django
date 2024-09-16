import os

from twilio.rest import Client


class TwilioUtility:
    def __init__(self):
        self.verify_service_sid = "VA4f9eec0402203e706790f45459d4d86e"
        account_sid = os.environ["TWILIO_ACCOUNT_SID"]
        auth_token = os.environ["TWILIO_AUTH_TOKEN"]
        self.client = Client(account_sid, auth_token)

    def send_verification_code(self, phone_number):
        try:
            self.client.verify.services(self.verify_service_sid).verifications.create(
                to=phone_number, channel="sms"
            )
            return True  # return True when the verification code is successfully sent
        except Exception as e:
            print(f"Error: {str(e)}")  # printing error for debugging purposes
            return False  # return False when there is an error

    def check_verification_code(self, phone_number, code):
        verification_check = self.client.verify.services(
            self.verify_service_sid
        ).verification_checks.create(to=phone_number, code=code)
        return verification_check.status == "approved"

    def get_phone_number_info(self, phone_number):
        try:
            phone_number_info = self.client.lookups.phone_numbers(phone_number).fetch(
                type=["carrier"]
            )

            return {
                "formatted_number": phone_number_info.phone_number,
                "country_code": phone_number_info.country_code,
                "carrier": phone_number_info.carrier,
            }
        except Exception as e:
            return None

    def fetch_available_numbers(self):
        return self.client.available_phone_numbers("US").local.list(
            sms_enabled=True, voice_enabled=True, mms_enabled=True, limit=1
        )

    def create_incoming_phone_number(self, phone_number, sms_url):
        return self.client.incoming_phone_numbers.create(
            phone_number=phone_number, sms_url=sms_url
        )

    def send_message(self, body, from_, to):
        return self.client.messages.create(body=body, from_=from_, to=to)