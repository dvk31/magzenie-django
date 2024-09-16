import json
import logging
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

def call_openai_api(data_to_send, template):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                template,
                data_to_send
            ],
            temperature=1,
            max_tokens=4095,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        logger.debug(f"OpenAI API response: {response}")

        try:
            json_response = response.choices[0].message.content
        except (AttributeError, IndexError) as e:
            logger.error(f"Error processing OpenAI response: {e}")
            return None, "Failed to process OpenAI response"
        
        return json_response, None

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return None, str(e)