import os
from mistralai.client import MistralClient
from openai import OpenAI
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)


# Instantiate the OpenAI client with your API key
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])



# Configuration for AI providers and their respective API keys
AI_PROVIDERS = {
    "mistral": {
        "api_key": os.getenv("MISTRAL_API_KEY"),
        "client": MistralClient,  # Directly use the class
        "models": {
            "mistral-large-latest": {
                "model": "mistral-large-latest",
                "response_format": {"type": "json_object"},
            },
        },
    },
    "openai": {  # Changed from "gpt-3.5" to "openai" to match your error message
        "client_class": OpenAI,
        "models": {
            "gpt-3.5-turbo": {
                "model": "gpt-3.5-turbo",
                "response_format": {"type": "json_object"},
            },
        },
    },
}

# Factory functions to create client instances for each provider
def create_mistral_client():
    from mistralai.client import MistralClient
    api_key = AI_PROVIDERS["mistral"]["api_key"]
    if not api_key:
        raise ValueError('MISTRAL_API_KEY is not set in the environment.')
    return MistralClient(api_key=api_key)



def create_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError('OPENAI_API_KEY is not set in the environment.')
    return AI_PROVIDERS["openai"]["client_class"](api_key=api_key)  # Corrected to "openai"

import openai

class AIService:
    def __init__(self):
        self.clients = {
            "mistral": create_mistral_client(),
            "openai": create_openai_client(),
        }
        self.models_config = {
            provider: config["models"] for provider, config in AI_PROVIDERS.items()
        }

    def get_chat_response(self, provider_name, model_name, messages):
        if provider_name in self.clients:
            client = self.clients[provider_name]
            model_config = self.models_config[provider_name].get(model_name)
            if not model_config:
                raise ValueError(f"Model '{model_name}' is not configured for provider '{provider_name}'.")
            if provider_name == "openai":
                return self._get_openai_chat_response(client, model_config['model'], messages)
            elif provider_name == "mistral":
                return self._get_mistral_chat_response(client, model_config['model'], messages)
            else:
                raise ValueError(f"Unsupported provider: {provider_name}")
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")

    def _get_openai_chat_response(self, client, model_name, messages):
        # Correct method call for OpenAI
        chat_response = client.ChatCompletion.create(
            model=model_name,
            messages=messages,
            max_tokens=150  # Set a reasonable default or derive from context
        )
        response_content = chat_response.choices[0].message.content
        return response_content

    def _get_mistral_chat_response(self, client, model_name, messages):
        # Implement Mistral-specific chat response logic here
        # Placeholder for actual implementation
        pass





    def _get_gpt3_5_chat_response(self, model_name, messages):
        client = self.clients['gpt-3.5']
        model_config = self.models_config['gpt-3.5'].get(model_name)
        if not model_config:
            raise ValueError(f"Model '{model_name}' is not configured for provider 'gpt-3.5'.")

        # Use the client instance to create a chat completion
        chat_response = client.chat.completions.create(
            model=model_config['model'],
            messages=messages
        )

        # Extract the relevant data from the ChatCompletion object
        # Assuming the response structure is similar to this:
        # {
        #   "choices": [
        #     {
        #       "message": {
        #         "content": "Response content here"
        #       }
        #     }
        #   ]
        # }
        response_content = chat_response.choices[0].message.content

        # Log the response content for debugging purposes
        logger.debug(f"OpenAI response content: {response_content}")

        # Return the response content directly without serialization,
        # since it's already a string
        return response_content