# user/agents.py

from django.apps import apps
from django.utils import timezone
from user.models import  DynamicModel, DynamicField, DynamicInstance, DynamicFieldValue, UserAIAgent, AIModels, Intent, UserInteraction, AgentManifest
from core.models.base_model import BaseModel
from userapp.models import UserApp
from .agents_utils import send_to_ai_model
from django.db.models import Q
from django.db import transaction
import json 
import logging
from groq import Groq
from django.conf import settings
logger = logging.getLogger(__name__)
from core.models.base_model import json_serialize
from uuid import UUID

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

class BaseAgent:
    def __init__(self, user):
        self.user = user
        self.ai_model = user.ai_agent.ai_model.name if user.ai_agent.ai_model else "gemma2-9b-it"

    def perform_crud(self, operation, model_name, data, app_label=None):
        if app_label is None:
            # Determine the app_label based on the model_name
            if model_name in ['UserApp']:
                app_label = 'userapp'
            elif model_name in ['User', 'RequestType', 'AIModels','UserProfile', 'Intent', 'UserInteraction', 'Category', 'DynamicModel', 'DynamicField', 'DynamicInstance', 'DynamicFieldValue']:
                app_label = 'user'
            else:
                app_label = 'core'  # Default to core for other models

        return BaseModel.perform_crud_operation(operation, app_label, model_name, data, user=self.user)
       
class UserAppAgent(BaseAgent):
    
    @transaction.atomic
    def get_or_create_app_by_intent(self, user_input, intent, context):
        try:
            app_name = f"{self.user.username}'s App - {intent}"
            app, created = UserApp.objects.get_or_create(
                user=self.user,
                name=app_name,
                defaults={
                    'description': f"App for intent: {intent}",
                    'is_active': True,
                    'last_used': timezone.now(),
                }
            )
            
            if created:
                intent_obj, _ = Intent.objects.get_or_create(name=intent)
                app.intents.add(intent_obj)
            
            app.last_used = timezone.now()
            app.save()
            
            return app, created
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error in get_or_create_app_by_intent: {str(e)}")
            raise

    @transaction.atomic
    def update_app_with_interaction(self, app, user_input, context):
        try:
            app.interaction_count = app.interaction_count + 1
            app.last_used = timezone.now()
            
            if 'interactions' not in app.config:
                app.config['interactions'] = []
            app.config['interactions'].append({
                'input': user_input,
                'timestamp': str(timezone.now()),
                'context': context
            })
            app.save()
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error updating app with interaction: {str(e)}")
            raise

    @transaction.atomic
    def link_resource_to_app(self, app_id, resource_type, resource_id):
        try:
            app = UserApp.objects.get(id=app_id)
            resource_model = apps.get_model('user', resource_type.capitalize())
            resource = resource_model.objects.get(id=resource_id)
            
            related_field = getattr(app, f'{resource_type}s', None)
            if related_field is None:
                raise ValueError(f"Invalid resource type: {resource_type}")
            
            related_field.add(resource)
            
            return {'status': 'success', 'message': f'{resource_type.capitalize()} linked to app successfully'}
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error linking resource to app: {str(e)}")
            raise

    @transaction.atomic
    def update_user_app(self, update_data):
        try:
            app = UserApp.objects.get(id=update_data['id'])
            for key, value in update_data.items():
                if key != 'id':
                    setattr(app, key, value)
            app.save()
            return {'status': 'success', 'message': 'App updated successfully'}
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error updating user app: {str(e)}")
            raise

    @transaction.atomic
    def create_new_app(self, user_input, context):
        try:
            app_name = f"{self.user.username}'s App - {context.get('intent', 'General')}"
            app_data = {
                'name': app_name,
                'description': f"App created from request: {user_input[:50]}...",
                'user': self.user.id,
                'is_active': True,
                'created_at': timezone.now(),
                'last_used': timezone.now(),
            }
            return self.perform_crud('create', 'UserApp', app_data)
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error creating new app: {str(e)}")
            raise

    def get_app_details(self, app_id):
        return self.perform_crud('read', 'UserApp', {'id': app_id})

    @transaction.atomic
    def process_task(self, user_input, task, context):
        try:
            intent = context.get('intent')
            if not intent:
                logger.error(f"No intent provided in context. Context: {context}")
                return {"status": "error", "details": {"error_message": "No intent provided in context"}}
            
            logger.info(f"Processing task for intent: {intent}")
            app, created = self.get_or_create_app_by_intent(user_input, intent, context)
            self.update_app_with_interaction(app, user_input, context)
            
            return {
                "status": "success",
                "details": {
                    "app_id": str(app.id),
                    "app_name": app.name,
                    "created": created,
                    "intent": intent
                }
            }
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error processing task: {str(e)}", exc_info=True)
            return {"status": "error", "details": {"error_message": str(e)}}

class RouterAgent:
    def __init__(self, user):
        self.user = user
        self.user_ai_agent = self.get_or_create_user_ai_agent()
        self.manifest = self.get_or_create_agent_manifest()
        self.ai_model = self.user_ai_agent.ai_model.name if self.user_ai_agent.ai_model else "gemma2-9b-it"

    def get_agent(self, agent_name):
        agent_map = {
            "IntentAgent": IntentAgent,
            "RequestAgent": RequestAgent,
            "DynamicModelAgent": DynamicModelAgent,
            "CategoryAgent": CategoryAgent,
            "UserProfileAgent": UserProfileAgent,
            "PersonaAgent": PersonaAgent,
            "AIModelAgent": AIModelAgent,
            "UserInteractionAgent": UserInteractionAgent,
            "UserAppAgent": UserAppAgent
        }
        
        agent_class = agent_map.get(agent_name)
        if agent_class:
            return agent_class(self.user)
        else:
            raise ValueError(f"Unknown agent: {agent_name}")

    @transaction.atomic
    def get_or_create_user_ai_agent(self):
        try:
            return UserAIAgent.objects.get(user=self.user)
        except UserAIAgent.DoesNotExist:
            default_ai_model = AIModels.get_default_model()
            default_intent = Intent.objects.filter(Q(user=self.user) | Q(user__isnull=True)).first()
            
            return UserAIAgent.objects.create(
                user=self.user,
                name=f"{self.user.username}'s AI Agent",
                is_default=True,
                intent=default_intent,
                ai_model=default_ai_model,
                last_interaction=timezone.now(),
                interaction_count=0,
                config={},
                input_token="",
                output_token="",
                total_cost=0.0
            )

    @transaction.atomic
    def get_or_create_agent_manifest(self):
        try:
            return AgentManifest.objects.get(agent=self.user_ai_agent)
        except AgentManifest.DoesNotExist:
            return AgentManifest.objects.create(
                agent=self.user_ai_agent,
                prompts={},
                functions={},
                context={},
                preferences={}
            )

    @transaction.atomic
    def log_interaction(self, user_input, agent_response, context):
        try:
            UserInteraction.objects.create(
                agent=self.user_ai_agent,
                user_input=user_input,
                agent_response=agent_response,
                context=context
            )
            self.user_ai_agent.interaction_count += 1
            self.user_ai_agent.last_interaction = timezone.now()
            self.user_ai_agent.save()
        except Exception as e:
            logger.error(f"Error logging interaction: {str(e)}", exc_info=True)
            raise

    @transaction.atomic
    def route_request(self, user_input, context):
        try:
            context = json.loads(json_serialize(context))
            
            routing_prompt = self.generate_routing_prompt(user_input, context)
            routing_decision = self.get_routing_decision(routing_prompt)
            result = self.execute_routing_plan(routing_decision, user_input, context)
            
            agent_response = json_serialize(result)
            return agent_response
        except Exception as e:
            logger.error(f"Error in route_request: {str(e)}", exc_info=True)
            return json_serialize({
                'status': 'error',
                'message': 'An error occurred while processing the request',
                'details': {'error_message': str(e)}
            })

    def generate_routing_prompt(self, user_input, context):
        available_agents = [
            "IntentAgent", "RequestAgent", "DynamicModelAgent", "CategoryAgent",
            "UserProfileAgent", "PersonaAgent", "AIModelAgent", "UserInteractionAgent"
        ]
        prompt = f"""
        As a RouterAgent, analyze the following user input and context to determine the optimal routing plan:

        User Input: "{user_input}"
        Context: {json_serialize(context)}

        Available Agents: {', '.join(available_agents)}

        Provide your routing plan as a JSON array of objects. Your response MUST be a valid JSON array starting with '[' and ending with ']'. Each object in the array should represent an agent call with the following structure:
        {{
            "agent": "AgentName",
            "order": int,
            "task": "Description of the task",
            "dependencies": ["AgentName1", "AgentName2"]
        }}

        Example of a valid response:
        [
            {{
                "agent": "IntentAgent",
                "order": 1,
                "task": "Identify user intent",
                "dependencies": []
            }},
            {{
                "agent": "CategoryAgent",
                "order": 2,
                "task": "Categorize the request",
                "dependencies": ["IntentAgent"]
            }}
        ]

        Ensure your response is a single JSON array containing all the agent calls. Do not include any text before or after the JSON array.
        """
        return prompt

    def get_routing_decision(self, routing_prompt):
        try:
            response = send_to_ai_model(routing_prompt, model=self.ai_model)
            
            logger.debug(f"Raw AI response: {response}")
            
            def ensure_order(item, index):
                if isinstance(item, dict) and 'order' not in item:
                    item['order'] = index + 1
                return item
            
            def process_response(resp):
                if isinstance(resp, list):
                    return [ensure_order(item, i) for i, item in enumerate(resp)]
                elif isinstance(resp, dict):
                    return [ensure_order(resp, 0)]
                elif isinstance(resp, str):
                    try:
                        parsed = json.loads(resp)
                        return process_response(parsed)
                    except json.JSONDecodeError:
                        return [{"error": "Invalid JSON", "raw_response": resp}]
                else:
                    return [{"error": "Unexpected response type", "raw_response": str(resp)}]
            
            routing_plan = process_response(response)
            
            # Ensure IntentAgent, UserAppAgent, and RequestAgent are included
            required_agents = ["IntentAgent", "UserAppAgent", "RequestAgent"]
            existing_agents = [step['agent'] for step in routing_plan if isinstance(step, dict) and 'agent' in step]
            
            for agent in required_agents:
                if agent not in existing_agents:
                    routing_plan.append({
                        "agent": agent,
                        "order": len(routing_plan) + 1,
                        "task": f"Process {agent.replace('Agent', '').lower()}",
                        "dependencies": required_agents[:required_agents.index(agent)]
                    })
            
            # Sort the routing plan by order
            routing_plan.sort(key=lambda x: x.get('order', 999) if isinstance(x, dict) else 999)
            
            logger.info(f"Final routing plan: {routing_plan}")
            return routing_plan

        except Exception as e:
            logger.error(f"Error in get_routing_decision: {str(e)}", exc_info=True)
            return [{"error": str(e)}]



    @transaction.atomic
    def execute_routing_plan(self, routing_plan, user_input, context):
        results = {}
        prompt_agent = PromptGenerationAgent(self.user)

        try:
            # Check if routing_plan is valid
            if not isinstance(routing_plan, list) or not routing_plan:
                raise ValueError("Invalid routing plan")

            # Execute IntentAgent first to determine the intent
            intent_agent = self.get_agent("IntentAgent")
            intent_context = context.copy()
            intent_context['agent_type'] = 'Intent'
            intent_prompt = prompt_agent.process_task(user_input, "Determine user intent", intent_context)
            logger.info(f"Executing IntentAgent with prompt: {intent_prompt}")
            intent_result = intent_agent.process_task(user_input, "Determine user intent", intent_prompt['details'])
            logger.info(f"Result from IntentAgent: {intent_result}")
            
            # Ensure the intent is properly set in the context
            if intent_result['status'] == 'success':
                context['intent'] = intent_result['details']['intent']
                logger.info(f"Intent determined: {context['intent']}")
            else:
                logger.error(f"Failed to determine intent: {intent_result}")
                return {"error": "Failed to determine intent", "details": intent_result}

            # Use UserAppAgent to get or create the app based on the intent
            user_app_agent = self.get_agent("UserAppAgent")
            app_context = context.copy()
            app_context['agent_type'] = 'UserApp'
            app_context['intent'] = context['intent']
            logger.info(f"Context for UserAppAgent: {app_context}")
            app_prompt = prompt_agent.process_task(user_input, "Get or create app by intent", app_context)
            logger.info(f"Executing UserAppAgent with prompt: {app_prompt}")
            app_result = user_app_agent.process_task(user_input, "Get or create app by intent", app_context)
            logger.info(f"Result from UserAppAgent: {app_result}")
            
            if app_result['status'] == 'success':
                context['app_id'] = app_result['details']['app_id']
                results['UserAppAgent'] = app_result
            else:
                logger.error(f"Failed to create or update UserApp: {app_result}")
                return {"error": "Failed to create or update UserApp", "details": app_result}

            # Execute the rest of the routing plan
            for step in sorted(routing_plan, key=lambda x: x.get('order', 999)):
                agent_name = step.get('agent')
                if not agent_name:
                    logger.warning(f"Skipping invalid step in routing plan: {step}")
                    continue
                
                if agent_name not in ['IntentAgent', 'UserAppAgent']:
                    agent = self.get_agent(agent_name)
                    
                    if all(dep in results for dep in step.get('dependencies', [])):
                        step_context = context.copy()
                        for dep in step.get('dependencies', []):
                            step_context[dep] = results[dep]
                        
                        # Generate prompt for the agent
                        step_context['agent_type'] = agent_name.replace('Agent', '')
                        step_context['intent'] = context['intent']
                        step_context['app_id'] = context['app_id']
                        prompt_result = prompt_agent.process_task(user_input, step.get('task', 'Unspecified task'), step_context)
                        if prompt_result['status'] == 'success':
                            step_context['prompt'] = prompt_result['details']['prompt']
                        else:
                            logger.warning(f"Failed to generate prompt for {agent_name}: {prompt_result}")
                        
                        logger.info(f"Executing {agent_name} with context: {step_context}")
                        result = agent.process_task(user_input, step.get('task', 'Unspecified task'), step_context)
                        logger.info(f"Result from {agent_name}: {result}")
                        results[agent_name] = result

                        if agent_name in ['DynamicModelAgent', 'CategoryAgent']:
                            self.link_resource_to_app(agent_name, result, context['app_id'])
                    else:
                        logger.warning(f"Dependencies not met for {agent_name}. Current results: {results}")
                        results[agent_name] = {"error": "Dependencies not met"}

            # Final step: Update UserApp with all created resources
            logger.info(f"Updating UserApp with results: {json_serialize(results)}")
            self.update_user_app_with_results(context['app_id'], results)

            return json.loads(json_serialize(results))
        except Exception as e:
            logger.error(f"Error in execute_routing_plan: {str(e)}", exc_info=True)
            transaction.set_rollback(True)
            return {"error": "An error occurred while executing the routing plan", "details": str(e)}

    def link_resource_to_app(self, agent_name, result, app_id):
        if result['status'] == 'success' and 'details' in result:
            resource_id = result['details'].get('id') or result['details'].get(f'{agent_name.lower()}_id')
            if resource_id:
                # Perform the linking logic here
                logger.info(f"Linking resource {resource_id} from {agent_name} to app {app_id}")
                # Add your linking logic here
            else:
                logger.warning(f"No resource ID found in result from {agent_name}")
        else:
            logger.warning(f"Unable to link resource from {agent_name} to app. Result: {result}")


    @transaction.atomic
    def update_user_app_with_results(self, app_id, results):
        try:
            user_app_agent = self.get_agent("UserAppAgent")
            update_data = {
                'id': app_id,
                'config': {
                    'last_interaction_results': json_serialize(results)
                }
            }
            user_app_agent.update_user_app(update_data)
        except Exception as e:
            logger.error(f"Error updating UserApp with results: {str(e)}", exc_info=True)
            raise

class IntentAgent(BaseAgent):
    def process_task(self, user_input, task, context):
        # Get all relevant intents (global and user-specific)
        all_intents = Intent.get_intents_for_ai(self.user)
        
        # Analyze the user input to determine the intent
        intent = self.analyze_intent(user_input, context, all_intents)
        
        # Check if the intent already exists
        existing_intent = Intent.get_user_or_global_intent(self.user, intent['name'])
        if existing_intent:
            return {
                'status': 'success',
                'details': {
                    'intent': existing_intent.name,
                    'intent_id': existing_intent.id,
                    'is_new': False
                }
            }
        
        # Create a new Intent based on the analysis
        new_intent, created = Intent.get_or_create_user_intent(
            user=self.user,
            name=intent['name'],
            description=intent['description'],
            keywords=intent.get('keywords', [])
        )
        
        return {
            'status': 'success',
            'details': {
                'intent': new_intent.name,
                'intent_id': new_intent.id,
                'is_new': created
            }
        }


    def analyze_intent(self, user_input, context, all_intents):
        # Prepare a prompt for the AI model to determine the intent
        prompt = f"""
        Analyze the following user input and determine the most appropriate intent.
        User input: "{user_input}"
        Context: {json.dumps(context)}

        Existing intents:
        {json.dumps(all_intents, indent=2)}

        Your task:
        1. If the user's input matches an existing intent (global or user-specific), return that intent.
        2. If no existing intent matches, create a new intent following the pattern of the global intents.

        Provide your response in the following JSON format:
        {{
            "intent_name": "Name of the intent (use camelCase)",
            "intent_description": "A brief description of the intent",
            "keywords": ["list", "of", "relevant", "keywords"],
            "is_existing": true/false
        }}

        Ensure that the intent_name is specific and meaningful, never return "Unknown" as an intent.
        """

        # Send the prompt to the AI model
        response = send_to_ai_model(prompt)

        # Handle the response
        if isinstance(response, dict):
            intent_data = response
        elif isinstance(response, list):
            # If it's a list, take the first item (assuming it's the intent data)
            intent_data = response[0] if response else {}
        elif isinstance(response, str):
            # If it's a string, try to parse it as JSON
            try:
                intent_data = json.loads(response)
            except json.JSONDecodeError:
                intent_data = {}
        else:
            intent_data = {}

        # Extract and return the relevant information
        return {
            'name': intent_data.get('intent_name', 'generalQuery'),
            'description': intent_data.get('intent_description', 'A general query or request from the user'),
            'keywords': intent_data.get('keywords', []),
            'is_existing': intent_data.get('is_existing', False)
        }

        
    # Keep the existing CRUD methods
    def create_intent(self, data):
        return self.perform_crud('create', 'Intent', data)

    def get_intent(self, intent_id):
        return self.perform_crud('read', 'Intent', {'id': intent_id})

    def update_intent(self, intent_id, data):
        data['id'] = intent_id
        return self.perform_crud('update', 'Intent', data)

    def delete_intent(self, intent_id):
        return self.perform_crud('delete', 'Intent', {'id': intent_id})

class RequestAgent(BaseAgent):
    def __init__(self, user):
        super().__init__(user)
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def process_task(self, user_input, task, context):
        try:
            logger.info(f"RequestAgent.process_task called with user_input: {user_input}, task: {task}, context: {context}")

            # Extract or create request type
            request_type = self.get_or_create_request_type(user_input, context)

            # Get or create intent
            intent = self.get_or_create_intent(context.get('intent'))

            # Create user request
            user_request = self.create_user_request(user_input, request_type, intent, context)

            # Get or create dynamic model for the request type
            dynamic_model = self.get_or_create_dynamic_model(request_type)

            # Use AI to analyze the request and suggest fields
            ai_analysis = self.analyze_request(user_input, request_type['name'], dynamic_model['name'])

            # Create dynamic instance and set field values
            dynamic_instance = self.create_dynamic_instance(dynamic_model['id'], ai_analysis['fields'])

            # Link dynamic instance to user request
            self.update_user_request(user_request['id'], {'dynamic_instance': dynamic_instance['id']})

            return {
                'status': 'success',
                'details': {
                    'request_id': user_request['id'],
                    'request_type': request_type['name'],
                    'intent': intent['name'],
                    'dynamic_instance_id': dynamic_instance['id'],
                    'fields': ai_analysis['fields']
                }
            }

        except Exception as e:
            logger.error(f"Error in RequestAgent.process_task: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'details': {
                    'error_message': str(e),
                    'error_type': type(e).__name__
                }
            }

    def get_or_create_request_type(self, user_input, context):
        request_type_name = context.get('request_type') or self.extract_request_type(user_input)
        result = self.perform_crud('create', 'RequestType', {
            'user': self.user.id,
            'name': request_type_name,
            'description': f"Request type for: {user_input[:50]}..."
        })
        return result['details']

    def get_or_create_intent(self, intent_name):
        result = self.perform_crud('create', 'Intent', {
            'user': self.user.id,
            'name': intent_name,
            'description': f"Intent for: {intent_name}"
        })
        return result['details']

    def create_user_request(self, user_input, request_type, intent, context):
        result = self.perform_crud('create', 'UserRequest', {
            'user': self.user.id,
            'request_type': request_type['id'],
            'intent': intent['id'],
            'initial_request': user_input,
            'is_active': True,
            'is_location_specific': context.get('is_location_specific', False),
            'visibility': 'private'
        })
        return result['details']

    def get_or_create_dynamic_model(self, request_type):
        result = self.perform_crud('create', 'DynamicModel', {
            'user': self.user.id,
            'name': f"{request_type['name']}_Model",
            'description': f"Dynamic model for request type: {request_type['name']}",
            'is_request_type': True
        })
        return result['details']

    def create_dynamic_instance(self, dynamic_model_id, fields):
        instance_result = self.perform_crud('create', 'DynamicInstance', {
            'model': dynamic_model_id,
            'user': self.user.id
        })
        
        for field_name, value in fields.items():
            field_result = self.perform_crud('read', 'DynamicField', {
                'model': dynamic_model_id,
                'name': field_name
            })
            if field_result['status'] == 'success':
                self.perform_crud('create', 'DynamicFieldValue', {
                    'instance': instance_result['details']['id'],
                    'field': field_result['details']['id'],
                    'value': value
                })
        
        return instance_result['details']

    def analyze_request(self, user_input, request_type, model_name):
        prompt = f"""
        Analyze the following user request and suggest appropriate fields and values:
        User Input: "{user_input}"
        Request Type: {request_type}
        Model Name: {model_name}

        Provide your response as a JSON object with a 'fields' property containing key-value pairs of suggested fields and their values.
        """
        
        response = self.send_to_ai_model(prompt)
        return response

    def send_to_ai_model(self, prompt):
        logger.info(f"Sending prompt to AI model: {prompt}")
        try:
            response = self.client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": "You are an AI assistant that helps analyze user requests and suggest appropriate fields and values. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.info(f"Received raw AI response: {content}")
            
            parsed_response = json.loads(content)
            logger.info(f"Parsed AI response: {parsed_response}")
            
            return parsed_response
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response causing JSON error: {content}")
            raise
        except Exception as e:
            logger.error(f"Error in send_to_ai_model: {str(e)}", exc_info=True)
            raise

    def extract_request_type(self, user_input):
        # This method could be enhanced with AI to better determine the request type
        words = user_input.lower().split()
        if 'developer' in words:
            return 'DeveloperRequest'
        elif 'job' in words:
            return 'JobRequest'
        else:
            return 'GeneralRequest'

    def update_user_request(self, request_id, data):
        result = self.perform_crud('update', 'UserRequest', {
            'id': request_id,
            **data
        })
        return result

    def get_user_request(self, request_id):
        result = self.perform_crud('read', 'UserRequest', {'id': request_id})
        if result['status'] == 'success':
            request_data = result['details']
            dynamic_instance_data = self.get_dynamic_instance_data(request_data.get('dynamic_instance'))
            return {
                'status': 'success',
                'details': {
                    'request_id': request_data['id'],
                    'request_type': request_data['request_type__name'],
                    'intent': request_data['intent__name'],
                    'initial_request': request_data['initial_request'],
                    'is_active': request_data['is_active'],
                    'is_location_specific': request_data['is_location_specific'],
                    'visibility': request_data['visibility'],
                    'dynamic_instance': dynamic_instance_data
                }
            }
        return result

    def get_dynamic_instance_data(self, instance_id):
        if not instance_id:
            return None
        field_values = self.perform_crud('read', 'DynamicFieldValue', {'instance': instance_id})
        if field_values['status'] == 'success':
            return {fv['field__name']: fv['value'] for fv in field_values['details']}
        return None

    def list_user_requests(self, filters=None):
        query = {'user': self.user.id}
        if filters:
            query.update(filters)
        result = self.perform_crud('read', 'UserRequest', query)
        if result['status'] == 'success':
            return {
                'status': 'success',
                'details': [
                    {
                        'request_id': req['id'],
                        'request_type': req['request_type__name'],
                        'intent': req['intent__name'],
                        'initial_request': req['initial_request'],
                        'is_active': req['is_active'],
                        'created_at': req['created_at']
                    }
                    for req in result['details']
                ]
            }
        return result



class IntentAnalysisAgent(BaseAgent):
    def analyze_intent(self, user_input, context):
        # Use AI to analyze the user's intent
        analysis_prompt = f"Analyze the intent of the following user input: '{user_input}'. Context: {json.dumps(context)}"
        analysis_result = send_to_ai_model(analysis_prompt)
        
        # Create or update an Intent based on the analysis
        intent_data = {
            'name': analysis_result['intent_name'],
            'description': analysis_result['intent_description'],
            'user': self.user.id,
        }
        return self.perform_crud('create', 'Intent', intent_data)

class ContextManagementAgent(BaseAgent):
    def update_context(self, current_context, new_data):
        updated_context = current_context.copy()
        updated_context.update(new_data)
        return updated_context

    def store_context(self, user_id, context):
        # Store the context for future interactions
        context_data = {
            'user': user_id,
            'context': json.dumps(context),
            'timestamp': timezone.now(),
        }
        return self.perform_crud('create', 'UserContext', context_data)

    def retrieve_latest_context(self, user_id):
        # Retrieve the latest context for the user
        return self.perform_crud('read', 'UserContext', {'user': user_id}, order_by='-timestamp')

class UserProfileAgent(BaseAgent):
    @transaction.atomic
    def create_user_profile(self, data):
        try:
            # Ensure the user is set
            data['user'] = self.user.id
            return self.perform_crud('create', 'UserProfile', data, app_label='user')
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error creating user profile: {str(e)}")
            return {'status': 'error', 'details': {'error_message': str(e)}}

    def get_user_profile(self, profile_id):
        return self.perform_crud('read', 'UserProfile', {'id': profile_id, 'user': self.user.id})

    def update_user_profile(self, profile_id, data):
        data['id'] = profile_id
        data['user'] = self.user.id
        return self.perform_crud('update', 'UserProfile', data)

    def delete_user_profile(self, profile_id):
        return self.perform_crud('delete', 'UserProfile', {'id': profile_id, 'user': self.user.id})

    def create_profile_type(self, data):
        data['user'] = self.user.id
        return self.perform_crud('create', 'ProfileType', data)

    def get_profile_type(self, profile_type_id):
        return self.perform_crud('read', 'ProfileType', {'id': profile_type_id, 'user': self.user.id})

    def update_profile_type(self, profile_type_id, data):
        data['id'] = profile_type_id
        data['user'] = self.user.id
        return self.perform_crud('update', 'ProfileType', data)

    def delete_profile_type(self, profile_type_id):
        return self.perform_crud('delete', 'ProfileType', {'id': profile_type_id, 'user': self.user.id})

    def create_user_profile_field(self, data):
        return self.perform_crud('create', 'UserProfileField', data)

    def get_user_profile_field(self, field_id):
        return self.perform_crud('read', 'UserProfileField', {'id': field_id})

    def update_user_profile_field(self, field_id, data):
        data['id'] = field_id
        return self.perform_crud('update', 'UserProfileField', data)

    def delete_user_profile_field(self, field_id):
        return self.perform_crud('delete', 'UserProfileField', {'id': field_id})

    def process_task(self, user_input, task, context):
        try:
            # Extract relevant information from user_input and context
            profile_type = context.get('profile_type') or self.extract_profile_type(user_input)
            
            if not profile_type:
                raise ValueError("Profile type could not be determined")

            # Create or update profile type
            profile_type_data = {
                'name': profile_type,
                'description': f"Profile type for: {user_input[:50]}..."
            }
            profile_type_result = self.create_profile_type(profile_type_data)
            
            if profile_type_result['status'] == 'error':
                raise Exception(profile_type_result['details']['error_message'])

            # Create user profile
            profile_data = {
                'profile_type': profile_type_result['details']['id'],
                'user': self.user.id
            }
            profile_result = self.create_user_profile(profile_data)
            
            if profile_result['status'] == 'error':
                raise Exception(profile_result['details']['error_message'])

            # Use AI to suggest fields for the profile
            ai_fields = self.suggest_profile_fields(user_input, profile_type)

            # Create profile fields
            for field in ai_fields:
                field_data = {
                    'profile': profile_result['details']['id'],
                    'field_name': field['name'],
                    'field_value': field['value']
                }
                field_result = self.create_user_profile_field(field_data)
                if field_result['status'] == 'error':
                    logger.warning(f"Failed to create field: {field['name']}")

            return {
                'status': 'success',
                'details': {
                    'profile_id': profile_result['details']['id'],
                    'profile_type': profile_type,
                    'fields_created': len(ai_fields)
                }
            }

        except Exception as e:
            logger.error(f"Error in UserProfileAgent.process_task: {str(e)}")
            return {
                'status': 'error',
                'details': {
                    'error_message': str(e)
                }
            }

    def extract_profile_type(self, user_input):
        # Implement logic to extract profile type from the user input
        # This could be based on a specific format in the input or from the context
        # For now, we'll use a simple placeholder implementation
        words = user_input.split()
        for i, word in enumerate(words):
            if word.lower() in ['profile', 'type']:
                return words[i+1] if i+1 < len(words) else None
        return None

    def suggest_profile_fields(self, user_input, profile_type):
        # Use AI to suggest fields for the profile
        prompt = f"""
        Based on the following user input and profile type, suggest appropriate fields for a user profile:
        User input: "{user_input}"
        Profile type: {profile_type}

        Provide your response as a JSON array of objects, where each object represents a field with 'name' and 'value' properties.
        """
        
        ai_response = self.send_to_ai_model(prompt)
        
        # Assuming the AI model returns a JSON string
        return json.loads(ai_response)

    def send_to_ai_model(self, prompt):
        # Placeholder method to send the prompt to the AI model and get a response
        # Replace with actual implementation using self.ai_model
        response = send_to_ai_model(prompt, model=self.ai_model)
        return response




class DynamicModelAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_agent = PromptGenerationAgent(*args, **kwargs)

    def process_task(self, user_input, task, context):
        try:
            logger.info(f"DynamicModelAgent.process_task called with user_input: {user_input}, task: {task}, context: {context}")

            # Use PromptGenerationAgent to generate the prompt and extract model name
            prompt_result = self.prompt_agent.process_task(user_input, task, {**context, 'agent_type': 'DynamicModel'})
            
            if prompt_result['status'] != 'success':
                raise ValueError(f"Failed to generate prompt: {prompt_result['details']['error_message']}")

            prompt = prompt_result['details']['prompt']
            model_name = self.prompt_agent.extract_model_name(user_input, context)
            
            logger.info(f"Using model_name: {model_name}")

            # Get or create the DynamicModel
            model_result = self.get_or_create_dynamic_model(model_name)
            if model_result['status'] == 'error':
                raise ValueError(f"Failed to get or create DynamicModel: {model_result['details']['error_message']}")

            # Use the imported send_to_ai_model function
            ai_response = send_to_ai_model(prompt)
            
            result = self.process_ai_response(model_name, ai_response)
            logger.info(f"Processed AI response: {result}")
            
            return result
        except Exception as e:
            logger.error(f"Error in DynamicModelAgent.process_task: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'details': {
                    'error_message': str(e),
                    'error_type': type(e).__name__
                }
            }

    def extract_model_name(self, user_input, context):
        model_name = context.get('model_name')
        if not model_name:
            model_name = self.extract_model_name_from_context(context)
        if not model_name:
            model_name = self.extract_model_name_from_input(user_input)
        if not model_name:
            intent = context.get('intent', 'General')
            model_name = f"{intent}Model"
        return model_name

    def get_or_create_dynamic_model(self, model_name):
        try:
            model, created = DynamicModel.objects.get_or_create(user=self.user, name=model_name)
            return {'status': 'success', 'details': {'id': model.id, 'name': model.name, 'created': created}}
        except Exception as e:
            logger.error(f"Error in get_or_create_dynamic_model: {str(e)}", exc_info=True)
            return {'status': 'error', 'details': {'error_message': str(e)}}

    def generate_ai_prompt(self, task, user_input, model_name, existing_fields):
        return (
            f"{task}\n\n"
            f"User Input: {user_input}\n\n"
            f"Existing fields: {json.dumps(existing_fields)}\n\n"
            f"Please update the dynamic model '{model_name}', avoiding duplicate fields. "
            f"For existing fields, you may update their properties. "
            f"For new fields, ensure they don't conflict with existing ones. "
            f"Format your response as JSON with 'updated_fields' and 'new_fields' arrays."
        )
    def get_existing_fields(self, model_name):
        fields = self.perform_crud('read', 'DynamicField', {'model__name': model_name})
        if fields['status'] == 'error':
            return []
        return [{'name': f['name'], 'field_type': f['field_type'], 'required': f['required'], 'choices': f['choices']} for f in fields['details']]

    def extract_model_name_from_context(self, context):
        # Try to extract model name from various context keys
        possible_keys = ['model_name', 'intent', 'app_name']
        for key in possible_keys:
            if key in context:
                return f"{context[key]}Model"
        return None
    
    def extract_model_name(self, user_input):
        logger.info(f"Attempting to extract model name from user input: {user_input}")
        words = user_input.split()
        for i, word in enumerate(words):
            if word.lower() in ['model', 'for']:
                if i+1 < len(words):
                    model_name = words[i+1]
                    logger.info(f"Extracted model name: {model_name}")
                    return model_name
                else:
                    logger.warning("Found 'model' or 'for' keyword, but no following word")
                    return None
        logger.warning("Could not extract model name from user input")
        return None

    def send_to_ai_model(self, prompt):
            logger.info(f"Sending prompt to AI model: {prompt}")
            try:
                response = self.client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": "You are an AI assistant that helps with creating and updating dynamic models. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                logger.info(f"Received raw AI response: {content}")
                
                # Parse the JSON content
                parsed_response = json.loads(content)
                logger.info(f"Parsed AI response: {parsed_response}")
                
                return parsed_response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response causing JSON error: {content}")
                raise
            except Exception as e:
                logger.error(f"Error in send_to_ai_model: {str(e)}", exc_info=True)
                raise

    def get_existing_fields(self, model_name):
        model = self.get_dynamic_model(model_name)
        if model['status'] == 'error':
            return []
        
        fields = self.perform_crud('read', 'DynamicField', {'model': model['details']['id']})
        if fields['status'] == 'error':
            return []
        
        return [{'name': f['name'], 'field_type': f['field_type'], 'required': f['required'], 'choices': f['choices']} for f in fields['details']]



    def process_ai_response(self, model_name, ai_response):
        try:
            logger.info(f"Processing AI response for model {model_name}: {ai_response}")
            
            if isinstance(ai_response, list):
                field_data_list = ai_response
            elif isinstance(ai_response, dict):
                field_data_list = ai_response.get('updated_fields', []) + ai_response.get('new_fields', [])
            else:
                raise ValueError(f"Unexpected AI response format: {type(ai_response)}")

            model = DynamicModel.objects.get(user=self.user, name=model_name)
            
            for field_data in field_data_list:
                if not isinstance(field_data, dict):
                    logger.warning(f"Skipping invalid field data: {field_data}")
                    continue
                
                field_name = field_data.get('name')
                if not field_name:
                    logger.warning(f"Skipping field data without name: {field_data}")
                    continue

                try:
                    existing_field = DynamicField.objects.get(model=model, name=field_name)
                    self.update_field(existing_field, field_data)
                except DynamicField.DoesNotExist:
                    self.create_field(model, field_data)

            return {
                'status': 'success', 
                'details': {
                    'model_id': model.id,  # No need to convert to string, UUIDEncoder will handle it
                    'model_name': model.name
                }
            }
        except Exception as e:
            logger.error(f"Error in process_ai_response: {str(e)}", exc_info=True)
            return {'status': 'error', 'details': {'error_message': str(e)}}

  
    def update_field(self, field, field_data):
        field.field_type = field_data.get('field_type', field.field_type)
        field.required = field_data.get('required', field.required)
        field.choices = field_data.get('choices', field.choices)
        field.save()
        logger.info(f"Updated field: {field.name}")

    def create_field(self, model, field_data):
        new_field = DynamicField.objects.create(
            model=model,
            name=field_data['name'],
            field_type=field_data.get('field_type', 'CharField'),
            required=field_data.get('required', False),
            choices=field_data.get('choices', None)
        )
        logger.info(f"Created new field: {new_field.name}")


    def create_dynamic_model(self, name, description, is_profile_type=False, is_request_type=False):
        data = {
            'name': name,
            'description': description,
            'is_profile_type': is_profile_type,
            'is_request_type': is_request_type,
            'user': self.user.id
        }
        return self.perform_crud('create', 'DynamicModel', data)

    def get_dynamic_model(self, name):
        return self.perform_crud('read', 'DynamicModel', {'name': name, 'user': self.user.id})

    def update_dynamic_model(self, name, new_data):
        model = self.get_dynamic_model(name)
        if model['status'] == 'error':
            return model
        new_data['id'] = model['details']['id']
        return self.perform_crud('update', 'DynamicModel', new_data)

    def delete_dynamic_model(self, name):
        model = self.get_dynamic_model(name)
        if model['status'] == 'error':
            return model
        return self.perform_crud('delete', 'DynamicModel', {'id': model['details']['id']})

    def update_field(self, model, field_data):
        try:
            field = DynamicField.objects.get(model=model, name=field_data['name'])
            field.field_type = field_data['field_type']
            field.required = field_data['required']
            field.save()
        except DynamicField.DoesNotExist:
            self.create_field(model, field_data)

    def create_field(self, model, field_data):
        DynamicField.objects.create(
            model=model,
            name=field_data['name'],
            field_type=field_data['field_type'],
            required=field_data['required']
        )
    def create_dynamic_field(self, model_name, field_name, field_type, required=False, choices=None):
        model = self.get_dynamic_model(model_name)
        if model['status'] == 'error':
            return model
        data = {
            'model': model['details']['id'],
            'name': field_name,
            'field_type': field_type,
            'required': required,
            'choices': choices
        }
        return self.perform_crud('create', 'DynamicField', data)

    def get_dynamic_field(self, model_name, field_name):
        model = self.get_dynamic_model(model_name)
        if model['status'] == 'error':
            return model
        return self.perform_crud('read', 'DynamicField', {'model': model['details']['id'], 'name': field_name})

    def update_dynamic_field(self, model_name, field_name, new_data):
        field = self.get_dynamic_field(model_name, field_name)
        if field['status'] == 'error':
            return field
        new_data['id'] = field['details']['id']
        return self.perform_crud('update', 'DynamicField', new_data)

    def delete_dynamic_field(self, model_name, field_name):
        field = self.get_dynamic_field(model_name, field_name)
        if field['status'] == 'error':
            return field
        return self.perform_crud('delete', 'DynamicField', {'id': field['details']['id']})

    def create_dynamic_instance(self, model_name, field_values):
        model = self.get_dynamic_model(model_name)
        if model['status'] == 'error':
            return model
        data = {
            'model': model['details']['id'],
            'user': self.user.id
        }
        instance = self.perform_crud('create', 'DynamicInstance', data)
        if instance['status'] == 'error':
            return instance
        
        for field_name, value in field_values.items():
            field = self.get_dynamic_field(model_name, field_name)
            if field['status'] == 'error':
                return field
            field_data = {
                'instance': instance['details']['id'],
                'field': field['details']['id'],
                'value': value
            }
            field_value = self.perform_crud('create', 'DynamicFieldValue', field_data)
            if field_value['status'] == 'error':
                return field_value
        
        return instance

    def get_dynamic_instance(self, model_name, instance_id):
        model = self.get_dynamic_model(model_name)
        if model['status'] == 'error':
            return model
        return self.perform_crud('read', 'DynamicInstance', {'id': instance_id, 'model': model['details']['id'], 'user': self.user.id})

    def get_dynamic_instances(self, model_name):
        model = self.get_dynamic_model(model_name)
        if model['status'] == 'error':
            return model
        return self.perform_crud('read', 'DynamicInstance', {'model': model['details']['id'], 'user': self.user.id})

    def update_dynamic_instance(self, model_name, instance_id, field_values):
        instance = self.get_dynamic_instance(model_name, instance_id)
        if instance['status'] == 'error':
            return instance
        
        for field_name, value in field_values.items():
            field = self.get_dynamic_field(model_name, field_name)
            if field['status'] == 'error':
                return field
            
            field_value = self.perform_crud('read', 'DynamicFieldValue', {'instance': instance_id, 'field': field['details']['id']})
            if field_value['status'] == 'error':
                field_value = self.perform_crud('create', 'DynamicFieldValue', {
                    'instance': instance_id,
                    'field': field['details']['id'],
                    'value': value
                })
            else:
                field_value = self.perform_crud('update', 'DynamicFieldValue', {
                    'id': field_value['details']['id'],
                    'value': value
                })
            
            if field_value['status'] == 'error':
                return field_value
        
        return {'status': 'success', 'message': 'Instance updated successfully'}

    def delete_dynamic_instance(self, model_name, instance_id):
        instance = self.get_dynamic_instance(model_name, instance_id)
        if instance['status'] == 'error':
            return instance
        return self.perform_crud('delete', 'DynamicInstance', {'id': instance_id})

    def get_instance_field_values(self, model_name, instance_id):
        instance = self.get_dynamic_instance(model_name, instance_id)
        if instance['status'] == 'error':
            return instance
        
        field_values = self.perform_crud('read', 'DynamicFieldValue', {'instance': instance_id})
        if field_values['status'] == 'error':
            return field_values
        
        return {
            'status': 'success',
            'details': {fv['field__name']: fv['value'] for fv in field_values['details']}
        }

    def link_model_to_app(self, model_id, app_id):
        app_data = {
            'id': app_id,
            'dynamic_models': [model_id]
        }
        return self.perform_crud('update', 'UserApp', app_data)


class CategoryAgent(BaseAgent):
    def __init__(self, user):
        super().__init__(user)
        self.client = Groq(api_key=settings.GROQ_API_KEY)

 
    def process_task(self, user_input, task, context):
        try:
            logger.info(f"CategoryAgent.process_task called with user_input: {user_input}, task: {task}, context: {context}")

            # Analyze the user input to determine the appropriate category
            category_name = self.analyze_category(user_input, context)
            
            # Get or create the category using perform_crud
            category_data = {
                'name': category_name,
                'description': f"Category for: {user_input[:50]}...",
                'user': self.user.id
            }
            result = self.perform_crud('create', 'Category', category_data)
            
            if result['status'] == 'success':
                return {
                    'status': 'success',
                    'details': {
                        'id': result['details']['id'],  # Ensure this line is present
                        'category_id': result['details']['id'],
                        'category_name': category_name,
                        'created': result['operation'] == 'create'
                    }
                }
            else:
                raise Exception(result['details'].get('error_message', 'Failed to create category'))

        except Exception as e:
            logger.error(f"Error in CategoryAgent.process_task: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'details': {
                    'error_message': str(e),
                    'error_type': type(e).__name__
                }
            }

        except Exception as e:
            logger.error(f"Error in CategoryAgent.process_task: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'details': {
                    'error_message': str(e),
                    'error_type': type(e).__name__
                }
            }

    def analyze_category(self, user_input, context):
        prompt = f"""
        Analyze the following user input and determine the most appropriate category:
        User input: "{user_input}"
        Context: {json.dumps(context)}

        Provide your response as a single category name (string).
        """
        
        logger.info(f"Sending prompt to AI model: {prompt}")
        try:
            response = self.client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": "You are an AI assistant that helps categorize user requests. Respond with a single category name."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            logger.info(f"Received AI response: {content}")
            
            # Ensure we're returning a string, not a list
            if isinstance(content, list):
                content = content[0] if content else ""
            
            return content.strip()
        except Exception as e:
            logger.error(f"Error in analyze_category: {str(e)}", exc_info=True)
            raise

    # Additional CRUD methods using BaseAgent's perform_crud
    def get_category(self, category_id):
        return self.perform_crud('read', 'Category', {'id': category_id})

    def update_category(self, category_id, data):
        data['id'] = category_id
        return self.perform_crud('update', 'Category', data)

    def delete_category(self, category_id):
        return self.perform_crud('delete', 'Category', {'id': category_id})

    def list_categories(self):
        # This might need a custom implementation depending on how you want to handle listing
        # For now, we'll return all categories for the user
        return self.perform_crud('read', 'Category', {'user': self.user.id})


class PersonaAgent(BaseAgent):
    def create_user_persona(self, data):
        return self.perform_crud('create', 'UserPersona', data)

    def get_user_persona(self, persona_id):
        return self.perform_crud('read', 'UserPersona', {'id': persona_id})

    def update_user_persona(self, persona_id, data):
        data['id'] = persona_id
        return self.perform_crud('update', 'UserPersona', data)

    def delete_user_persona(self, persona_id):
        return self.perform_crud('delete', 'UserPersona', {'id': persona_id})


class AIModelAgent(BaseAgent):
    def process_task(self, user_input, task, context):
        try:
            logger.info(f"AIModelAgent.process_task called with user_input: {user_input}, task: {task}, context: {context}")

            # Determine the appropriate AI model based on the task and context
            ai_model = self.determine_ai_model(task, context)

            # Get or create the AI model
            model_data = {
                'name': ai_model,
                'user': self.user.id,
                'provider': self.determine_provider(ai_model),
                'is_free': self.is_free_model(ai_model),
                'cost_per_token': self.get_cost_per_token(ai_model)
            }
            result = self.perform_crud('create', 'AIModels', model_data)

            if result['status'] == 'success':
                return {
                    'status': 'success',
                    'details': {
                        'id': result['details']['id'],
                        'model_name': ai_model,
                        'provider': model_data['provider'],
                        'is_free': model_data['is_free'],
                        'cost_per_token': model_data['cost_per_token']
                    }
                }
            else:
                raise Exception(result['details'].get('error_message', 'Failed to create AI model'))

        except Exception as e:
            logger.error(f"Error in AIModelAgent.process_task: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'details': {
                    'error_message': str(e),
                    'error_type': type(e).__name__
                }
            }

    def determine_ai_model(self, task, context):
        # This method should implement logic to choose the appropriate AI model
        # based on the task and context. For now, we'll use a simple implementation.
        if 'complex' in task.lower():
            return 'gpt-4'
        elif 'code' in task.lower() or context.get('intent') == 'FindReactDeveloper':
            return 'gemma2-9b-it'
        else:
            return 'gpt-3.5-turbo'

    def determine_provider(self, model_name):
        if model_name.startswith('gpt'):
            return 'openai'
        elif model_name.startswith('gemma'):
            return 'gorq'
        else:
            return 'custom'

    def is_free_model(self, model_name):
        # Implement logic to determine if the model is free
        return model_name in ['gemma2-9b-it']

    def get_cost_per_token(self, model_name):
        # Implement logic to determine the cost per token for each model
        cost_map = {
            'gpt-4': 0.0002,
            'gpt-3.5-turbo': 0.00001,
            'gemma2-9b-it': 0.0001
        }
        return cost_map.get(model_name, 0.0001)  # Default to 0.0001 if not found

    # Additional CRUD methods
    def get_ai_model(self, model_id):
        return self.perform_crud('read', 'AIModels', {'id': model_id})

    def update_ai_model(self, model_id, data):
        data['id'] = model_id
        return self.perform_crud('update', 'AIModels', data)

    def delete_ai_model(self, model_id):
        return self.perform_crud('delete', 'AIModels', {'id': model_id})

    def list_ai_models(self):
        return self.perform_crud('read', 'AIModels', {'user': self.user.id})


class UserInteractionAgent(BaseAgent):
    @transaction.atomic
    def create_user_interaction(self, data):
        try:
            return self.perform_crud('create', 'UserInteraction', data, app_label='user')
        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"Error creating user interaction: {str(e)}")
            raise

    def get_user_interaction(self, interaction_id):
        return self.perform_crud('read', 'UserInteraction', {'id': interaction_id})

    def update_user_interaction(self, interaction_id, data):
        data['id'] = interaction_id
        return self.perform_crud('update', 'UserInteraction', data)

    def delete_user_interaction(self, interaction_id):
        return self.perform_crud('delete', 'UserInteraction', {'id': interaction_id})

class PromptGenerationAgent(BaseAgent):
    def get_prompt_template(self, agent_type):
        templates = {
            'DynamicModel': "For the input '{user_input}' and context {context}, update or create a dynamic model named '{model_name}'. You will be provided with existing fields. Avoid creating duplicate fields. You may update properties of existing fields if necessary. For new fields, ensure they don't conflict with existing ones. Format your response as JSON with 'updated_fields' and 'new_fields' arrays, each containing objects with 'name', 'field_type', and 'required' properties.",
            'Category': "Analyze the following user input and determine the most appropriate category: User input: '{user_input}'. Context: {context}. Provide your response as a single category name (string).",
            'Intent': "Determine the user's intent based on the following input: '{user_input}'. Context: {context}. Provide your response as a single intent name (string).",
            'UserProfile': "Based on the user input '{user_input}' and context {context}, suggest appropriate fields for a user profile. Provide your response as a JSON array of objects, where each object represents a field with 'name' and 'value' properties.",
            'AIModel': "Based on the task '{task}' and context {context}, determine the most appropriate AI model to use. Consider factors such as complexity, specific requirements, and any mentioned technologies or frameworks.",
            'Request': "Analyze the following user request and suggest appropriate fields and values: User Input: '{user_input}'. Request Type: {request_type}. Provide your response as a JSON object with a 'fields' property containing key-value pairs of suggested fields and their values.",
            'UserApp': "Process the following request: '{user_input}'. Intent: {intent}. Create or update an app for this intent.",
        }
        return templates.get(agent_type, "Process the following request: {user_input}")

    def generate_prompt(self, agent_type, user_input, context):
        prompt_template = self.get_prompt_template(agent_type)
        if agent_type == 'DynamicModel':
            model_name = self.extract_model_name(user_input, context)
            existing_fields = self.get_existing_fields(model_name)
            filled_prompt = prompt_template.format(
                user_input=user_input,
                context=json.dumps(context),
                model_name=model_name
            )
            filled_prompt += f"\n\nExisting fields: {json.dumps(existing_fields)}"
        else:
            filled_prompt = self.fill_prompt_template(prompt_template, user_input, context)
        logger.info(f"Generated prompt for {agent_type}: {filled_prompt}")
        return filled_prompt

    def extract_model_name(self, user_input, context):
        logger.info(f"Extracting model name from user input: {user_input} and context: {context}")
        # First, try to extract from context
        model_name = context.get('model_name')
        if model_name:
            logger.info(f"Model name found in context: {model_name}")
            return model_name

        # If not in context, try to extract from user input
        words = user_input.split()
        for i, word in enumerate(words):
            if word.lower() in ['model', 'for']:
                if i+1 < len(words):
                    model_name = words[i+1]
                    logger.info(f"Extracted model name from user input: {model_name}")
                    return model_name

        # If we couldn't extract a name, use a default based on the intent
        intent = context.get('intent', 'General')
        default_name = f"{intent}Model"
        logger.info(f"Using default model name: {default_name}")
        return default_name

    def get_existing_fields(self, model_name):
        logger.info(f"Fetching existing fields for model: {model_name}")
        try:
            model = DynamicModel.objects.get(name=model_name, user=self.user)
            fields = DynamicField.objects.filter(model=model)
            existing_fields = [
                {
                    'name': field.name,
                    'field_type': field.field_type,
                    'required': field.required,
                    'choices': field.choices
                }
                for field in fields
            ]
            logger.info(f"Existing fields for {model_name}: {json.dumps(existing_fields)}")
            return existing_fields
        except DynamicModel.DoesNotExist:
            logger.warning(f"No existing model found for {model_name}")
            return []
        except Exception as e:
            logger.error(f"Error fetching existing fields for {model_name}: {str(e)}")
            return []

    def fill_prompt_template(self, template, user_input, context):
        filled_prompt = template.format(
            user_input=user_input,
            context=json.dumps(context),
            task=context.get('task', 'Unspecified task'),
            request_type=context.get('request_type', 'Unspecified request type'),
            intent=context.get('intent', 'Unspecified intent')
        )
        logger.info(f"Filled prompt template: {filled_prompt}")
        return filled_prompt

    def process_task(self, user_input, task, context):
        try:
            logger.info(f"PromptGenerationAgent.process_task called with user_input: {user_input}, task: {task}, context: {context}")
            agent_type = context.get('agent_type', 'General')
            prompt = self.generate_prompt(agent_type, user_input, context)
            return {
                'status': 'success',
                'details': {
                    'prompt': prompt,
                    'agent_type': agent_type
                }
            }
        except Exception as e:
            logger.error(f"Error in PromptGenerationAgent.process_task: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'details': {
                    'error_message': str(e),
                    'error_type': type(e).__name__
                }
            }
 

class AgentFactory:
    @staticmethod
    def get_agent(agent_type, user):
        agents = {
            'UserProfile': UserProfileAgent,
            'Request': RequestAgent,
            'DynamicModel': DynamicModelAgent,
            'Intent': IntentAgent,
            'Category': CategoryAgent,
            'Persona': PersonaAgent,
            'AIModel': AIModelAgent,
            'UserInteraction': UserInteractionAgent,
            'UserApp': UserAppAgent
        }
        agent_class = agents.get(agent_type)
        if agent_class:
            return agent_class(user)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

