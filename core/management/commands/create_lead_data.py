import json
import logging
import traceback
import os
import requests
import pytz
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from datetime import datetime
from agency.models import LeadData, Lead, Agency, LeadStatus, DeclineReason

# Set up logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populate LeadData and Lead from external API for a specific agency'

    def add_arguments(self, parser):
        parser.add_argument('agency_uuid', type=str, help='UUID of the agency')

    def handle(self, *args, **kwargs):
        agency_uuid = kwargs['agency_uuid']
        
        try:
            agency = Agency.objects.get(id=agency_uuid)
        except Agency.DoesNotExist:
            raise CommandError(f'Agency with UUID {agency_uuid} does not exist')

        try:
            leads_data = self.fetch_leads_data()
            self.populate_lead_data(leads_data, agency)
            self.convert_existing_lead_data_to_agency_timezone(agency)
        except Exception as e:
            logger.error("An error occurred: %s", str(e))
            logger.error(traceback.format_exc())

    def fetch_leads_data(self):
        base_url = os.getenv('SUPABASE_API_URL')
        api_url = f"{base_url}/rest/v1/rpc/get_all_leads"
        headers = {
            "Content-Type": "application/json",
            "apikey": os.getenv('SUPABASE_API_KEY'),
            "Authorization": f"Bearer {os.getenv('SUPABASE_API_KEY')}"
        }
        logger.info("Fetching leads data from API")
        response = requests.post(api_url, headers=headers)
        response.raise_for_status()
        leads_data = response.json()
        logger.info("Successfully fetched leads data")
        return leads_data

    def populate_lead_data(self, leads_data, agency):
        logger.info("Starting to populate LeadData and Lead")
        with transaction.atomic():
            for lead in leads_data:
                lead_data_instance = self.create_or_update_lead_data(lead, agency)
                self.create_or_update_lead(lead, lead_data_instance, agency)
        logger.info("Successfully populated LeadData and Lead")

    def create_or_update_lead_data(self, lead, agency):
        logger.debug("Processing lead data: %s", lead)
        lead['created_at'] = self.convert_to_agency_timezone(lead['created_at'], agency.time_zone)
        lead_data_instance, created = LeadData.objects.update_or_create(
            id=lead['id'],
            defaults={
                'agency': agency,
                'full_name': lead['full_name'],
                'email': lead['email'],
                'phone': lead.get('phone'),
                'dot_number': lead.get('dot_number'),
                'mc_number': lead.get('mc_number'),
                'landing_page_id': lead.get('landing_page_id'),
                'last_contacted': lead.get('last_contacted'),
                'next_followup_date': lead.get('next_followup_date'),
                'notes': lead.get('notes'),
                'created_at': lead['created_at'],
                'zip': lead.get('zip'),
                'dot_info': lead.get('dot_info'),
                'is_webhook_triggered': lead['is_webhook_triggered'],
                'ip_address': lead.get('ip_address'),
                'page_uuid': lead.get('page_uuid'),
                'variant': lead.get('variant'),
                'time_submitted': lead.get('time_submitted'),
                'date_submitted': lead.get('date_submitted'),
                'page_url': lead.get('page_url'),
                'page_name': lead.get('page_name'),
            }
        )
        return lead_data_instance

    def create_or_update_lead(self, lead, lead_data_instance, agency):
        logger.debug("Processing lead: %s", lead)
        status = LeadStatus.objects.filter(id=lead.get('status_id')).first()
        decline_reason = DeclineReason.objects.filter(id=lead.get('decline_reason_id')).first()
        Lead.objects.update_or_create(
            lead_data=lead_data_instance,
            agency=agency,
            defaults={
                'created_at': lead['created_at'],
                'status': status,
                'decline_reason': decline_reason,
                'customer': lead_data_instance,  # Assuming customer is same as lead_data_instance, adjust if needed
            }
        )

    def convert_to_agency_timezone(self, utc_datetime_str, agency_time_zone):
        utc_datetime = datetime.fromisoformat(utc_datetime_str)
        agency_tz = pytz.timezone(agency_time_zone)
        return utc_datetime.astimezone(agency_tz)

    def convert_existing_lead_data_to_agency_timezone(self, agency):
        logger.info("Converting existing LeadData and Lead to agency time zone")
        leads_data = LeadData.objects.filter(agency=agency)
        with transaction.atomic():
            for lead_data in leads_data:
                if lead_data.created_at:
                    lead_data.created_at = self.convert_to_agency_timezone(lead_data.created_at.isoformat(), agency.time_zone)
                    lead_data.save()
        leads = Lead.objects.filter(agency=agency)
        with transaction.atomic():
            for lead in leads:
                if lead.created_at:
                    lead.created_at = self.convert_to_agency_timezone(lead.created_at.isoformat(), agency.time_zone)
                    lead.save()
        logger.info("Successfully converted existing LeadData and Lead to agency time zone")

