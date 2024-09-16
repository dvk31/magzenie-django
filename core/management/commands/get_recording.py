import os
import base64
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime, timedelta
from department.models import CallLog, CallRecording, PhoneNumber
from agency.models import Agency
from uuid import UUID
import uuid
from django.utils import timezone

import logging
from django.db import transaction
from django.db.utils import IntegrityError

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import call logs and recordings from CSV and MP3 files'

    def add_arguments(self, parser):
        parser.add_argument('agency_id', type=UUID, help='UUID of the agency')

    def handle(self, *args, **kwargs):
        logger = logging.getLogger(__name__)
        agency_id = kwargs['agency_id']
        agency = self.get_agency(agency_id, logger)
        if not agency:
            return

        # Correct the path to the calllog directory
        calllog_path = '/Users/pc/Dropbox/ablelabs/aisurance/calllog'
        logger.info(f'Looking for call logs in: {calllog_path}')

        # Check if the directory exists before proceeding
        if not os.path.exists(calllog_path):
            logger.error(f'Call log directory not found at {calllog_path}')
            self.stdout.write(self.style.ERROR(f'Call log directory not found at {calllog_path}'))
            return

        csv_file = self.find_csv_file(calllog_path, logger)
        if not csv_file:
            return

        if not self.process_csv_file(csv_file, agency, calllog_path, logger):
            return

        logger.info('Call logs and recordings imported successfully')
        self.stdout.write(self.style.SUCCESS('Call logs and recordings imported successfully'))


    def get_agency(self, agency_id, logger):
        try:
            return Agency.objects.get(pk=agency_id)
        except Agency.DoesNotExist:
            logger.error(f'Agency with ID {agency_id} does not exist')
            self.stdout.write(self.style.ERROR(f'Agency with ID {agency_id} does not exist'))
            return None

    def find_csv_file(self, calllog_path, logger):
        try:
            for file in os.listdir(calllog_path):
                if file.endswith('.csv'):
                    return os.path.join(calllog_path, file)
        except FileNotFoundError as e:
            logger.error(f'Error finding CSV file: {str(e)}')
            self.stdout.write(self.style.ERROR('No CSV file found in calllog directory'))
        return None

    def process_csv_file(self, csv_file, agency, calllog_path, logger):
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:  # 'utf-8-sig' to handle BOM
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                logger.info(f'CSV Headers: {headers}')

                for row in reader:
                    self.process_csv_row(row, agency, calllog_path, logger)
            return True
        except Exception as e:
            logger.exception('Failed to process the CSV file: %s', str(e))
            self.stdout.write(self.style.ERROR('Failed to process the CSV file'))
            return False



    def process_csv_row(self, row, agency, calllog_path, logger):
        with transaction.atomic():
            start_time, end_time = self.parse_times(row)
            from_phone_number, to_phone_number = self.get_phone_numbers(row)
            call_log = self.create_call_log(row, agency, start_time, end_time, from_phone_number, to_phone_number)
            if not self.match_mp3_files(row, call_log, calllog_path, agency, logger):
                logger.warning(f'Processing row for call log {call_log.id} completed, but MP3 file not found.')
        return True



    def parse_times(self, row):
        start_time = datetime.strptime(row['Date'] + ' ' + row['Time'], '%a %m/%d/%Y %I:%M %p')
        start_time = timezone.make_aware(start_time, timezone.get_default_timezone())
        duration_parts = row['Duration'].split(':')
        duration = int(duration_parts[0]) * 3600 + int(duration_parts[1]) * 60 + int(duration_parts[2])
        end_time = start_time + timedelta(seconds=duration)
        return start_time, end_time  # Remove the second make_aware call



    def get_phone_numbers(self, row):
        from_phone_number, _ = PhoneNumber.objects.get_or_create(number=row['From'])
        to_phone_number, _ = PhoneNumber.objects.get_or_create(number=row['To'])
        return from_phone_number, to_phone_number

    def create_call_log(self, row, agency, start_time, end_time, from_phone_number, to_phone_number):
        return CallLog.objects.create(
            agency=agency,
            call_id=row.get('call_id', str(uuid.uuid4())),  # Generate a UUID if call_id is not present
            session_id=row.get('session_id', None),
            start_time=start_time,
            end_time=end_time,
            duration=(end_time - start_time).seconds,
            type=row.get('Type', 'unknown'),
            direction=row.get('Direction', 'unknown'),
            action=row.get('Action', 'unknown'),
            result=row.get('Action Result', 'unknown'),
            from_phone_number=from_phone_number,
            to_phone_number=to_phone_number,
            from_name=row.get('Name', None),
            to_name=row.get('To Name', None),
            recording_id=row.get('recording_id', None),
            recording_status=row.get('recording_status', None),
            recording_duration=row.get('recording_duration', None),
            recording_url=row.get('recording_url', None),
            recording_content_type=row.get('recording_content_type', None),
            recording_size=row.get('recording_size', None),
            status_code=row.get('status_code', None),
            status_rcc=row.get('status_rcc', None),
            missed_call=row.get('missed_call', None),
            stand_alone=row.get('stand_alone', None),
            muted=row.get('muted', None),
            account_id=row.get('account_id', None),
            extension_id=row.get('extension_id', None),
            call_direction=row.get('call_direction', None)
        )


    def match_mp3_files(self, row, call_log, calllog_path, agency, logger):
        recording_id = row.get('recording_id') or str(uuid.uuid4())  # Use existing or generate a new UUID

        matched_file = None
        for file in os.listdir(calllog_path):
            if file.endswith('.mp3'):
                # Check for a match using the recording_id if it exists
                if row.get('recording_id') and row['recording_id'] in file:
                    matched_file = file
                    break
                # Fallback: match based on other criteria if recording_id is not provided
                elif self.is_potential_match(row, file):
                    matched_file = file
                    break

        if matched_file:
            with open(os.path.join(calllog_path, matched_file), 'rb') as mp3_file:
                recording_content = base64.b64encode(mp3_file.read()).decode('utf-8')
                CallRecording.objects.create(
                    agency=agency,
                    call_analysis_agent=None,
                    call_log=call_log,
                    recording_id=recording_id,
                    recording_type=row.get('recording_type', 'unknown'),
                    recording_content=recording_content,
                    is_ai_processed=False,
                    ai_response=None,
                    ai_meta_data=None,
                    ismeta_data_processed=False,
                    recording_context_agent=None,
                    extracted_intent=None
                )
            logger.info(f'MP3 file {matched_file} matched and processed for recording ID {recording_id}')
            return True

        logger.error(f'MP3 file matching recording ID {recording_id} not found for call log {call_log.id}')
        return False

    def is_potential_match(self, row, file):
        # Implement additional matching logic if needed
        return False
