import logging
from django.conf import settings
from pinecone import Pinecone

logger = logging.getLogger(__name__)

class PineconeHelper:
    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = "aisurance"

    def query_index(self, query_vector, top_k=10):
        try:
            index = self.pc.Index(self.index_name)
            # Convert query_vector to list
            query_vector = query_vector.tolist()
            results = index.query(vector=query_vector, top_k=top_k)
            return results
        except Exception as e:
            logger.error(f"Error querying Pinecone index: {e}")
            return None
