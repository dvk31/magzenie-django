import os
from django.core.management.base import BaseCommand
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

class Command(BaseCommand):
    help = 'Send a test email using SendGrid'

    def handle(self, *args, **kwargs):
        message = Mail(
            from_email='davidl@hellofeed.xyz',
            to_emails='drkanel103@gmail.com',
            subject='Sending with Twilio SendGrid is Fun',
            html_content='<strong>and easy to do anywhere, even with Python</strong>'
        )
        try:
            sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            response = sg.send(message)
            self.stdout.write(self.style.SUCCESS('Email sent successfully!'))
            self.stdout.write(f'Status Code: {response.status_code}')
            self.stdout.write(f'Body: {response.body}')
            self.stdout.write(f'Headers: {response.headers}')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
