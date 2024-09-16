# clients.py
from django.conf import settings
from openai import OpenAI as RealOpenAIClient
from .mock_openai_client import MockOpenAIClient



def get_openai_client():
    if getattr(settings, 'USE_MOCK_OPENAI_CLIENT', False):
        return MockOpenAIClient()
    else:
        import openai
        return openai