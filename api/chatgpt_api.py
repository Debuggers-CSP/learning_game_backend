
"""
ChatGPT (OpenAI) API for handling requests to the language model.
Supports text analysis, citation checking, and other AI-powered features.

Example frontend JavaScript code for reference:
const API_KEY = "your-api-key-here";
const ENDPOINT = "https://api.openai.com/v1/chat/completions";
fetch(ENDPOINT, {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${API_KEY}`
    },
    body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [
            { role: "system", content: "You are a helpful assistant." },
            { role: "user", content: `Please look at this text for correct academic citations, and recommend APA references for each area of concern: ${text}` }
        ]
    })
});
"""
from __init__ import app
from flask import Blueprint, request, jsonify, current_app, g
from flask_restful import Api, Resource
import requests
from api.jwt_authorize import token_required

chatgpt_api = Blueprint('chatgpt_api', __name__, url_prefix='/api')
api = Api(chatgpt_api)

def _normalize_model(model_name: str) -> str:
    if not model_name:
        return model_name
    name = model_name.strip()
    if name.lower() == 'chatgpt-5.2':
        return 'gpt-5.2'
    return name

class ChatGPTAPI:
    class _Ask(Resource):
        """
        ChatGPT API Resource to handle requests to the language model.
        Supports various AI-powered text analysis tasks.
        """
        @token_required()
        def post(self):
            """
            Send a request to the ChatGPT API.
            
            Expected JSON body:
            {
                "text": "Text to analyze",
                "prompt": "Optional custom prompt" (defaults to citation analysis)
            }
            
            Returns:
                JSON response from ChatGPT API or error message
            """
            current_user = g.current_user
            body = request.get_json()
            
            # Validate request body
            if not body:
                return {'message': 'Request body is required'}, 400
            
            text = body.get('text', '')
            if not text:
                return {'message': 'Text field is required'}, 400
            
            # Get configuration
            api_key = app.config.get('OPENAI_API_KEY')
            server = app.config.get('OPENAI_SERVER') or 'https://api.openai.com/v1/chat/completions'
            default_model = _normalize_model(app.config.get('OPENAI_MODEL') or 'gpt-4o-mini')
            
            if not api_key:
                return {'message': 'OpenAI API key not configured'}, 500

            if not server:
                return {'message': 'OpenAI server not configured'}, 500

            # Build the endpoint URL
            endpoint = server
            
            # Default prompt for citation analysis, can be overridden
            default_prompt = "Please look at this text for correct academic citations, and recommend APA references for each area of concern"
            prompt = body.get('prompt', default_prompt)

            # Allow overriding model per request (e.g., ChatGPT 5.2)
            # Accepts aliases: "chatgpt-5.2" -> "gpt-5.2"
            requested_model = body.get('model')
            if requested_model:
                model = _normalize_model(requested_model)
            else:
                model = default_model
            
            # Prepare the request payload for OpenAI ChatGPT
            payload = {
                "model": model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"{prompt}: {text}"}
                ]
            }
            
            # Log the request for auditing purposes
            current_app.logger.info(f"User {current_user.uid} made a ChatGPT API request")
            
            try:
                # Log the request details for debugging
                current_app.logger.info(f"Making request to OpenAI API: {endpoint}")
                current_app.logger.debug(f"Payload: {payload}")
                
                # Make request to OpenAI API
                response = requests.post(
                    endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {api_key}'
                    },
                    json=payload,
                    timeout=90  # 90 second timeout
                )
                
                # Check if the request was successful
                if response.status_code != 200:
                    error_details = {
                        'status_code': response.status_code,
                        'response_text': response.text,
                        'endpoint': endpoint,
                        'headers': dict(response.headers)
                    }
                    current_app.logger.error(f"OpenAI API error: {error_details}")
                    
                    # Handle specific error codes
                    if response.status_code == 503:
                        return {
                            'message': 'OpenAI API is temporarily unavailable (503). Please try again later.',
                            'error_code': 503,
                            'details': 'The service may be overloaded or under maintenance.'
                        }, 503
                    elif response.status_code == 429:
                        return {
                            'message': 'Rate limit exceeded. Please try again later.',
                            'error_code': 429
                        }, 429
                    elif response.status_code == 400:
                        return {
                            'message': 'Bad request to OpenAI API. Please check your input.',
                            'error_code': 400,
                            'details': response.text
                        }, 400
                    else:
                        return {
                            'message': f'OpenAI API error: {response.status_code}',
                            'error_code': response.status_code,
                            'details': response.text
                        }, 500
                
                # Parse the response
                result = response.json()
                
                # Extract the generated text
                try:
                    generated_text = result['choices'][0]['message']['content']
                    return {
                        'success': True,
                        'text': generated_text,
                        'user': current_user.uid
                    }
                except (KeyError, IndexError) as e:
                    current_app.logger.error(f"Error parsing OpenAI response: {e}")
                    return {
                        'success': False,
                        'message': 'Error parsing OpenAI API response',
                        'raw_response': result
                    }, 500
                    
            except requests.RequestException as e:
                current_app.logger.error(f"Error communicating with OpenAI API: {e}")
                return {'message': f'Error communicating with OpenAI API: {str(e)}'}, 500
            except Exception as e:
                current_app.logger.error(f"Unexpected error in OpenAI API: {e}")
                return {'message': f'Unexpected error: {str(e)}'}, 500

    class _Health(Resource):
        """
        Health check endpoint for OpenAI API integration.
        """
        @token_required()
        def get(self):
            """
            Check if ChatGPT API is properly configured.
            
            Returns:
                JSON response indicating configuration status
            """
            api_key = app.config.get('OPENAI_API_KEY')
            server = app.config.get('OPENAI_SERVER') or 'https://api.openai.com/v1/chat/completions'
            model = _normalize_model(app.config.get('OPENAI_MODEL') or 'gpt-4o-mini')
            
            # Test the API endpoint if configured
            status_info = {
                'openai_configured': bool(api_key and server),
                'server': server if server else 'Not configured',
                'api_key_present': bool(api_key),
                'model': model
            }
            
            if api_key and server:
                try:
                    # Make a simple test request to check API availability
                    test_endpoint = server
                    test_payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": "Hello"}
                        ]
                    }
                    
                    response = requests.post(
                        test_endpoint,
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {api_key}'
                        },
                        json=test_payload,
                        timeout=10
                    )
                    
                    status_info['api_test'] = {
                        'status_code': response.status_code,
                        'available': response.status_code == 200
                    }
                    
                    if response.status_code != 200:
                        status_info['api_test']['error'] = response.text
                        
                except Exception as e:
                    status_info['api_test'] = {
                        'available': False,
                        'error': str(e)
                    }
            
            return status_info

    class _Debug(Resource):
        """
        Debug endpoint to help troubleshoot OpenAI API issues.
        """
        @token_required()
        def post(self):
            """
            Debug the OpenAI API request to identify 503 issues.
            
            Returns detailed information about the request and response.
            """
            current_user = g.current_user
            body = request.get_json()
            
            # Get configuration
            api_key = app.config.get('OPENAI_API_KEY')
            server = app.config.get('OPENAI_SERVER') or 'https://api.openai.com/v1/chat/completions'
            model = _normalize_model(app.config.get('OPENAI_MODEL') or 'gpt-4o-mini')
            
            debug_info = {
                'user': current_user.uid,
                'config_check': {
                    'api_key_present': bool(api_key),
                    'api_key_length': len(api_key) if api_key else 0,
                    'server': server,
                    'server_valid': bool(server and server.startswith('https://'))
                },
                'request_body': body,
                'default_model': model
            }
            
            if not api_key or not server:
                debug_info['error'] = 'Missing API configuration'
                return debug_info, 500
            
            # Build the endpoint URL
            endpoint = server
            debug_info['endpoint'] = endpoint
            
            # Simple test payload
            test_payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Test"}
                ]
            }
            
            try:
                response = requests.post(
                    endpoint,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {api_key}'
                    },
                    json=test_payload,
                    timeout=30
                )
                
                debug_info['response'] = {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'content': response.text[:500] if response.text else None  # Limit content length
                }
                
                return debug_info
                
            except Exception as e:
                debug_info['exception'] = str(e)
                return debug_info, 500

    # Register endpoints
    api.add_resource(_Ask, '/chatgpt')
    api.add_resource(_Health, '/chatgpt/health')
    api.add_resource(_Debug, '/chatgpt/debug')