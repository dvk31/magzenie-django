from django.core.management.base import BaseCommand, CommandError
from space.models import Space, IndustryType, FeedType, SpaceFeed
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update the industry type of a specific space'

    def add_arguments(self, parser):
        parser.add_argument('space_id', type=str, help='The ID of the space to update')
        parser.add_argument('industry_type_id', type=str, help='The ID of the industry type to set')

    def handle(self, *args, **kwargs):
        space_id = kwargs['space_id']
        industry_type_id = kwargs['industry_type_id']

        try:
            space = Space.objects.get(id=space_id)
            industry_type = IndustryType.objects.get(id=industry_type_id)

            space.industry_type = industry_type
            space.save()

            self.create_feed_types_for_industry(space, industry_type)

            self.stdout.write(self.style.SUCCESS(f'Successfully updated industry type for space {space_id}'))
        except Space.DoesNotExist:
            raise CommandError(f'Space with ID {space_id} does not exist')
        except IndustryType.DoesNotExist:
            raise CommandError(f'Industry type with ID {industry_type_id} does not exist')
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise CommandError(f'An unexpected error occurred: {e}')

    def create_feed_types_for_industry(self, space, industry_type):
        templates = industry_type.space_templates.all()
        for template in templates:
            feed_types = template.template.get('feed_types', [])
            space_feed = SpaceFeed.objects.create(
                name=f"{industry_type.name} Feed",
                description=f"Feed for {industry_type.name} industry"
            )
            for feed_type_name in feed_types:
                feed_type, created = FeedType.objects.update_or_create(
                    name=feed_type_name,
                    defaults={'description': f'{feed_type_name} for {industry_type.name}'}
                )
                space_feed.feed_types.add(feed_type)
            space_feed.save()