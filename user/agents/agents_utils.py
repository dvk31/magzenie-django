

import json
import logging 
import os
from groq import Groq

logger = logging.getLogger(__name__)

def send_to_ai_model(prompt, model="llama3-70b-8192", temperature=1, max_tokens=3320):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assistant that helps with routing decisions. Always respond with a valid JSON array."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=1,
            stream=False,
            
            stop=None,
        )
        
        # Extract the content from the response
        response_content = completion.choices[0].message.content
        
        # Log the raw response for debugging
        logger.debug(f"Raw AI response: {response_content}")
        
        # Parse the JSON content
        parsed_response = json.loads(response_content)
        
        return parsed_response
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Raw response causing JSON error: {response_content}")
        raise
    except Exception as e:
        logger.error(f"Error in send_to_ai_model: {str(e)}")
        raise


# Example usage:
if __name__ == "__main__":
    prompt = """
    You are a RouterAgent responsible for analyzing user input and context to determine the optimal routing plan for processing a request in a complex AI-driven system. Your task is to create an efficient routing plan that utilizes various specialized agents to handle different aspects of the user's request.

    User Input: "find me a react developer with at least 5 years of experience who can work remotely"

    Context: {
        "user_id": "user123",
        "user_role": "recruiter",
        "active_searches": [],
        "last_interaction": "2023-04-15T14:30:00Z",
        "preferred_ai_tone": "professional"
    }

    Available Agents:
    - IntentAgent: Analyzes user intent and classifies requests
    - RequestAgent: Creates structured requests based on user input
    - DynamicModelAgent: Manages dynamic data models for various entity types
    - CategoryAgent: Categorizes requests and entities
    - UserProfileAgent: Searches and manages user profiles
    - PersonaAgent: Manages and switches between user personas
    - AIModelAgent: Selects appropriate AI models for specific tasks
    - UserInteractionAgent: Logs user interactions and updates context

    For each relevant agent, specify:
    1. The order in which it should be called
    2. The specific task it should perform
    3. Any dependencies on other agents' outputs

    Consider the following:
    - The user's intent and the type of request
    - Any specific models or data that need to be created or updated
    - The need for user profile searches or updates
    - Appropriate categorization of the request
    - Logging and context updates

    Provide your routing plan as a JSON array of objects, where each object represents an agent call with the following structure:
    {
        "agent": "AgentName",
        "order": int,
        "task": "Description of the task",
        "dependencies": ["AgentName1", "AgentName2"]
    }

    Ensure the routing plan is efficient and addresses all aspects of the user's request.
    """
    
    response = send_to_ai_model(prompt)
    print(json.dumps(response, indent=2))
