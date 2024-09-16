import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from emails.models import EmailMessage, EmailData, SpaceEmailAnalysisCriteria, CriteriaIgnore, CriteriaAdvanceAnalysis
from space.models import Space, SpaceFeed, SpaceFeedData
from user.models import UsersModel 
from emails.models.email_analyzer import EmailAnalyzer  # Ensure this is the correct import path
import os
from django.conf import settings
logger = logging.getLogger(__name__)
import json

class Command(BaseCommand):
    help = 'Create a test EmailMessage and trigger analysis'

    def handle(self, *args, **kwargs):
        try:
            user = self.get_or_create_user()
            space_instance = self.get_or_create_space(user)
            space_feed_data_instance = self.get_or_create_space_feed_data(space_instance)
            space_feed_instance = self.get_or_create_space_feed(space_instance)
            email_data = self.create_email_data(space_instance, space_feed_data_instance, space_feed_instance)
            email_message = self.create_email_message(space_instance, space_feed_data_instance, space_feed_instance, email_data)

            self.stdout.write(self.style.SUCCESS(f'Successfully created EmailMessage with ID {email_message.id}'))

            # Create analysis criteria
            self.create_analysis_criteria(space_instance)

            # Trigger the analysis
            self.trigger_analysis(email_message)
        except Exception as e:
            logger.error(f"Error creating test email: {str(e)}")
            self.stderr.write(self.style.ERROR(f'Error creating test email: {str(e)}'))

    def get_or_create_user(self):
        user, created = UsersModel.objects.get_or_create(
            username='testuser',
            defaults={'email': 'testuser@example.com', 'password': 'password123'}
        )
        if created:
            logger.info(f'Created new user with username {user.username}')
        else:
            logger.info(f'Using existing user with username {user.username}')
        return user

    def get_or_create_space(self, user):
        space, created = Space.objects.get_or_create(
            name="Test Space",
            defaults={'owner': user, 'time_zone': 'America/Los_Angeles'}
        )
        if created:
            logger.info(f'Created new space with name {space.name}')
        else:
            logger.info(f'Using existing space with name {space.name}')
        return space

    def get_or_create_space_feed_data(self, space):
        space_feed_data, created = SpaceFeedData.objects.get_or_create(
            space=space,
            name="Test Feed Data"
        )
        if created:
            logger.info(f'Created new space feed data with name {space_feed_data.name}')
        else:
            logger.info(f'Using existing space feed data with name {space_feed_data.name}')
        return space_feed_data

    def get_or_create_space_feed(self, space):
        space_feed, created = SpaceFeed.objects.get_or_create(
            space=space,
            name="Test Feed"
        )
        if created:
            logger.info(f'Created new space feed with name {space_feed.name}')
        else:
            logger.info(f'Using existing space feed with name {space_feed.name}')
        return space_feed

    def create_email_data(self, space, space_feed_data, space_feed):
        email_data, created = EmailData.objects.get_or_create(
            space=space,
            defaults={'space_feed_data': space_feed_data, 'space_feed': space_feed}
        )
        if created:
            logger.info(f'Created new EmailData with ID {email_data.id}')
        else:
            logger.info(f'Using existing EmailData with ID {email_data.id}')
        
        # Optionally update fields if they might have changed
        email_data.space_feed_data = space_feed_data
        email_data.space_feed = space_feed
        email_data.save()

        return email_data

    def create_email_message(self, space, space_feed_data, space_feed, email_data):
        email_message = EmailMessage.objects.create(
            space=space,
            space_feed_data=space_feed_data,
            space_feed=space_feed,
            sender_name="John Doe",
            sender_email="john.doe@example.com",
            recipient_name="Jane Smith",
            recipient_email="jane.smith@example.com",
            subject="Test Email",
            content="This is a test email.",  # Assuming 'content' is the correct field name
            body_html="<p>This is a test email.</p>",  # Added field for HTML content
            received_at=timezone.now(),
            email_data=email_data
        )
        logger.info(f'Created new EmailMessage with ID {email_message.id}')
        return email_message

    def create_analysis_criteria(self, space):
        json_file_path = os.path.join(settings.BASE_DIR, '..', 'emails', 'models', 'matching_criteria.json')
        with open(json_file_path, 'r') as json_file:
            criteria_data = json.load(json_file)
        
        ignore_criteria_list = []
        for ignore_data in criteria_data['ignore_criteria']:
            ignore_criteria, created = CriteriaIgnore.objects.get_or_create(
                space=space,
                name=ignore_data['name'],
                defaults=ignore_data
            )
            ignore_criteria_list.append(ignore_criteria)
        
        advance_criteria_list = []
        for advance_data in criteria_data['advance_analysis_criteria']:
            advance_criteria, created = CriteriaAdvanceAnalysis.objects.get_or_create(
                space=space,
                name=advance_data['name'],
                defaults=advance_data
            )
            advance_criteria_list.append(advance_criteria)
        
        SpaceEmailAnalysisCriteria.objects.get_or_create(
            space=space,
            defaults={
                'space_second_analysis_ai_agent': criteria_data['space_second_analysis_ai_agent'],
                'space_advanced_analysis_ai_agent': criteria_data['space_advanced_analysis_ai_agent'],
                'ignore_criteria': ignore_criteria_list,
                'advance_analysis_criteria': advance_criteria_list,
            }
        )

    def trigger_analysis(self, email_message):
        try:
            json_file_path = os.path.join(settings.BASE_DIR, '..', 'emails', 'models', 'analysis_criteria.json')
            analyzer = EmailAnalyzer(config_path=json_file_path)
            analyzer.analyze_email(email_message)
            logger.info(f'Successfully triggered analysis for EmailMessage ID {email_message.id}')
        except Exception as e:
            logger.error(f"Error triggering analysis for EmailMessage ID {email_message.id}: {str(e)}")