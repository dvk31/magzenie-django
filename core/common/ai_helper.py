import logging
from openai import OpenAI
from django.conf import settings
from .pinecone_helper import PineconeHelper
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class AIHelper:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.pinecone_helper = PineconeHelper()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def query_pinecone(self, data_to_send):
        query_vector = self.model.encode(data_to_send)
        logger.debug(f"Query vector: {query_vector}")  # Log the query vector
        results = self.pinecone_helper.query_index(query_vector)
        logger.debug(f"Pinecone query results: {results}")  # Log the results
        return results

    def call_openai_api(self, data_to_send, template):
        try:
            # Query Pinecone for relevant data
            pinecone_results = self.query_pinecone(data_to_send)
            if not pinecone_results:
                return None, "Failed to retrieve relevant data from Pinecone"

            # Prepare context from Pinecone results
            context = "\n".join([str(item) for item in pinecone_results['matches']])

            # Call OpenAI API with context and template
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    template,
                    {"role": "system", "content": context},
                    {"role": "user", "content": data_to_send}
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