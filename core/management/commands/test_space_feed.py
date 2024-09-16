from django.core.management.base import BaseCommand, CommandError
from emails.models import EmailMessage, EmailData, SpaceFeedData, SpaceFeed
from django.db.models import Prefetch
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test the get_prefetched_space_feed method for all EmailMessages where send_to_email_feed is True and associate the SpaceFeed'

    def handle(self, *args, **options):
        try:
            email_messages = EmailMessage.objects.filter(send_to_email_feed=True)
            
            for email_message in email_messages:
                email_data = email_message.email_data
                space_feed = self.get_prefetched_space_feed(email_data)
                
                if space_feed:
                    email_message.email_feed = space_feed
                    email_message.save()
                    self.stdout.write(self.style.SUCCESS(f"Successfully associated SpaceFeed with EmailMessage ID: {email_message.id}"))
                    self.stdout.write(self.style.SUCCESS(f" - SpaceFeed: {space_feed.name} (ID: {space_feed.id})"))
                else:
                    self.stdout.write(self.style.WARNING(f"No SpaceFeed found for EmailMessage ID: {email_message.id}"))
        
        except EmailMessage.DoesNotExist:
            raise CommandError("No EmailMessage found with send_to_email_feed set to True.")
    
    def get_prefetched_space_feed(self, email_data):
        try:
            space_feed = SpaceFeed.objects.prefetch_related(
                Prefetch('feed_data', queryset=SpaceFeedData.objects.filter(space=email_data.space))
            ).get(pk=email_data.space_feed_id)
            return space_feed
        except SpaceFeed.DoesNotExist:
            logger.error(f"No SpaceFeed found for space feed ID: {email_data.space_feed_id}")
            return None