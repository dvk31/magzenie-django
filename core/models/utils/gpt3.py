# aiassitant/tasks/gpt3.py

import logging
import os

import openai
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger(__name__)


class ChatWithGPT3:
    def run(self, messages):
        try:
            logger.debug("Sending messages to GPT-3.5 Turbo: %s", messages)
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
            )
            logger.debug("Received reply from GPT-3.5 Turbo: %s", response)
            return response
        except Exception as e:
            logger.error("Error while chatting with GPT-3.5 Turbo: %s", e)
            raise e
