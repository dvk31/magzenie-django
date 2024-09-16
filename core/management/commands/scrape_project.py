import os
from datetime import datetime
import re
import json
import logging
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Scrape files from the specified folder'

    def handle(self, *args, **options):
        config_file = os.path.join(os.path.dirname(__file__), 'scrape_config.json')
        if not os.path.exists(config_file):
            logger.error(f"Configuration file '{config_file}' not found.")
            self.stdout.write(self.style.ERROR(f"Configuration file '{config_file}' not found."))
            return

        with open(config_file, 'r') as f:
            config = json.load(f)

        folder = config.get('folder')
        file_types = config.get('file_types', [])
        exclude_folders = config.get('exclude_folders', [])

        if not folder:
            logger.error("Folder not specified in the configuration file.")
            self.stdout.write(self.style.ERROR("Folder not specified in the configuration file."))
            return

        logger.info(f"Starting scraping for folder: {folder}")
        scraper = ProjectScraper(folder, file_types, exclude_folders)
        filename = scraper.run()

        with open(filename, 'r', encoding='utf-8') as file:
            file_content = file.read()

        logger.info(f"Scraping completed. Results saved to: {filename}")
        self.stdout.write(self.style.SUCCESS(file_content))

class ProjectScraper:
    def __init__(self, folder, file_types=None, exclude_folders=None):
        if file_types is None:
            file_types = []
        if exclude_folders is None:
            exclude_folders = []
        self.folder = os.path.abspath(folder)
        self.file_types = file_types
        self.exclude_folders = exclude_folders

    def fetch_all_files(self):
        files_data = []
        for root, dirs, files in os.walk(self.folder):
            dirs[:] = [d for d in dirs if d not in self.exclude_folders]
            for file in files:
                if any(file.endswith(file_type) for file_type in self.file_types):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    files_data.append(f"\n'''--- {file_path} ---\n{file_content}\n'''")
        return files_data

    def write_to_file(self, files_data):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"project_scrape_{timestamp}.txt"
        with open(filename, "w", encoding='utf-8') as f:
            f.write(f"*Project Scrape*\n")
            for file_data in files_data:
                f.write(file_data)
        return filename

    def clean_up_text(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read()
        cleaned_text = re.sub('\n{3,}', '\n\n', text)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)

    def run(self):
        logger.info("Fetching all files...")
        files_data = self.fetch_all_files()
        logger.info("Writing to file...")
        filename = self.write_to_file(files_data)
        logger.info("Cleaning up file...")
        self.clean_up_text(filename)
        logger.info("Done.")
        return filename