import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Retrieves the content from multiple pages of the Postman documentation and saves it as a text file'

    def handle(self, *args, **options):
        main_url = 'https://documenter.getpostman.com/view/17108315/UVXjHahb'
        output_file = 'postman_docs_all.txt'

        # Set up Selenium with Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Ensure GUI is off
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        
        # Load the main URL
        driver.get(main_url)
        time.sleep(5)  # Wait for page to load completely

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all the links to the pages within the documentation
        page_links = soup.select('.collection-sidebar-list-item a')

        # Extract the text content from each page
        text_content = ''
        for link in page_links:
            page_url = link['href']
            if not page_url.startswith('http'):
                page_url = f'https://documenter.getpostman.com{page_url}'

            # Load each page URL
            driver.get(page_url)
            time.sleep(5)  # Wait for page to load completely

            # Wait for the main content container to be present
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'markdown-body'))
            )

            # Parse the HTML content of the page using BeautifulSoup
            page_soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Find the main content container of the page
            content_container = page_soup.find('div', class_='markdown-body')

            if content_container:
                # Extract the text content from the page
                page_text = content_container.get_text(separator='\n', strip=True)

                # Debug print to check the extracted content
                print(f'Extracted content from {page_url}:\n{page_text[:500]}...')  # Print first 500 chars

                # Append the page content to the overall text content
                text_content += f'\n\n--- Page: {page_url} ---\n\n{page_text}'
            else:
                self.stdout.write(self.style.WARNING(f'Content container not found for page: {page_url}'))

            # Log the complete page source for debugging
            with open(f'page_source_{page_url.split("/")[-1]}.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)

        # Save the entire text content to a file
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(text_content)

        self.stdout.write(self.style.SUCCESS(f'Content saved to {output_file}'))

        # Close the browser
        driver.quit()