"""
LLM service integrations
"""
import logging
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import requests
import time

logger = logging.getLogger(__name__)


class LLMService:
    """Base class for LLM services"""
    
    def generate(self, prompt: str) -> str:
        raise NotImplementedError
    
    def is_available(self) -> bool:
        raise NotImplementedError


class BedrockService(LLMService):
    """AWS Bedrock service"""
    
    def __init__(self, region: str, model_id: str, routing_model_id: str = None, conversational_model_id: str = None):
        self.region = region
        self.model_id = model_id
        self.routing_model_id = routing_model_id or model_id
        self.conversational_model_id = conversational_model_id or model_id
        self.client = None
        self.available = False
        self._init_client()
    
    def _init_client(self):
        try:
            self.client = boto3.client('bedrock-runtime', region_name=self.region)
            self.available = True
            logger.info(f"Bedrock client initialized - Main: {self.model_id}, Routing: {self.routing_model_id}, Conversational: {self.conversational_model_id}")
        except Exception as e:
            logger.warning(f"Bedrock not available: {e}")
            self.available = False
        try:
            self.client = boto3.client('bedrock-runtime', region_name=self.region)
            # Just check if we can create the client - actual availability checked on first use
            self.available = True
            logger.info(f"Bedrock client initialized - Main: {self.model_id}, Routing: {self.routing_model_id}")
        except Exception as e:
            logger.warning(f"Bedrock not available: {e}")
            self.available = False
    
    def is_available(self) -> bool:
        return self.available
    
    def generate(self, prompt: str, use_routing_model: bool = False, has_conversation_history: bool = False) -> str:
        """Generate response. Set use_routing_model=True for fast classification, has_conversation_history=True for context-aware responses."""
        if has_conversation_history:
            model_id = self.conversational_model_id
        elif use_routing_model:
            model_id = self.routing_model_id
        else:
            model_id = self.model_id
            
        start_time = time.time()
        logger.info(f"Attempting Bedrock API call with {model_id}")
        
        # Determine if it's Claude or Nova model
        is_claude = 'claude' in model_id.lower()
        is_nova = 'nova' in model_id.lower()
        
        if is_claude:
            # Claude models use Messages API format
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        elif is_nova:
            # Nova models use different format
            body = json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": 1000,
                    "temperature": 0.7
                }
            })
        else:
            # Fallback to Claude format
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        
        try:
            response = self.client.invoke_model(
                modelId=model_id,
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            
            # Parse response based on model type
            if is_nova:
                answer = response_body['output']['message']['content'][0]['text']
            else:
                answer = response_body['content'][0]['text']
            
            elapsed = time.time() - start_time
            logger.info(f"Bedrock API call successful - {elapsed:.2f}s")
            return answer
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"Bedrock API error [{error_code}]: {error_msg}")
    
    def stream_generate(self, prompt: str):
        """Stream tokens from Bedrock in real-time."""
        logger.info("Starting Bedrock streaming API call")
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
        
        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=body
            )
            
            # Stream tokens as they arrive
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'])
                
                if chunk['type'] == 'content_block_delta':
                    if 'delta' in chunk and 'text' in chunk['delta']:
                        yield chunk['delta']['text']
                elif chunk['type'] == 'message_stop':
                    break
            
            logger.info("Bedrock streaming completed")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"Bedrock streaming error [{error_code}]: {error_msg}")
            raise Exception(f"Bedrock API error: {error_msg}")
            
            if error_code == 'AccessDeniedException':
                self.available = False
                raise ValueError("Bedrock access denied - check IAM permissions")
            elif error_code == 'ThrottlingException':
                raise ValueError("Bedrock rate limit exceeded")
            else:
                raise ValueError(f"Bedrock API error: {error_msg}")
        except Exception as e:
            logger.error(f"Bedrock unexpected error: {e}")
            raise ValueError(f"Bedrock API failed: {e}")


class GrokService(LLMService):
    """Grok API service"""
    
    def __init__(self, api_key: str, base_url: str, model: str, max_tokens: int):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.available = self._validate_key()
    
    def _validate_key(self) -> bool:
        if not self.api_key or self.api_key == '${GROK_API_KEY}':
            logger.warning("Grok API key not set")
            return False
        return True
    
    def is_available(self) -> bool:
        return self.available
    
    def stream_generate(self, prompt: str):
        """Stream tokens from Grok in real-time."""
        logger.info("Starting Grok streaming API call")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': self.max_tokens,
            'stream': True
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=30
            )
            
            response.raise_for_status()
            
            # Stream tokens
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield delta['content']
                        except json.JSONDecodeError:
                            continue
            
            logger.info("Grok streaming completed")
            
        except Exception as e:
            logger.error(f"Grok streaming error: {e}")
            raise Exception(f"Grok API failed: {e}")
    
    def generate(self, prompt: str) -> str:
        start_time = time.time()
        logger.info("Attempting Grok API call")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': self.max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 401:
                logger.error("Grok API: Invalid API key")
                self.available = False
                raise ValueError("Invalid Grok API key")
            elif response.status_code == 429:
                logger.error("Grok API: Rate limit exceeded")
                raise ValueError("Grok API rate limit exceeded")
            elif response.status_code == 500:
                logger.error("Grok API: Server error")
                raise ValueError("Grok API server error")
            
            response.raise_for_status()
            
            data = response.json()
            if 'choices' not in data or not data['choices']:
                raise ValueError("Invalid Grok API response format")
            
            answer = data['choices'][0]['message']['content']
            
            elapsed = time.time() - start_time
            logger.info(f"Grok API call successful - {elapsed:.2f}s")
            return answer
            
        except requests.exceptions.Timeout:
            logger.error("Grok API: Request timeout")
            raise ValueError("Grok API request timeout")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Grok API: Connection error - {e}")
            raise ValueError("Grok API connection error")
        except requests.exceptions.RequestException as e:
            logger.error(f"Grok API: Request failed - {e}")
            raise ValueError(f"Grok API request failed: {e}")
            raise ValueError("Grok API timeout")
        except requests.exceptions.ConnectionError:
            logger.error("Grok API: Connection error")
            raise ValueError("Grok API connection failed")
        except requests.exceptions.RequestException as e:
            logger.error(f"Grok API: Request failed - {e}")
            raise ValueError(f"Grok API request failed: {str(e)}")
