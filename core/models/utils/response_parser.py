# ai_parser.py

import json
import logging

logger = logging.getLogger(__name__)


class AiResponseParser:
    def parse_response(self, ai_response):
        try:
            if "choices" in ai_response and ai_response["choices"]:
                message = ai_response["choices"][0].get("message")
                if message and "content" in message:
                    content = message["content"]
                    logger.debug(f"Attempting to parse content: {content}")
                    try:
                        content = content.replace("'", '"')
                        content_json = json.loads(content)
                        intent_name = content_json.get("intent", "")
                        return {"intent": intent_name}
                    except json.JSONDecodeError:
                        logger.error("Could not parse 'content' as JSON.")
                        return None
                else:
                    logger.error(
                        "No 'message' object or 'content' field in AI response."
                    )
                    return None
            else:
                logger.error("No 'choices' in AI response or 'choices' array is empty.")
                return None
        except Exception as e:
            logger.error(
                f"An error occurred when parsing the AI response: {e}. AI response: {ai_response}"
            )
            return None
