"""LLM integration for summarization and action items using Ollama via OpenWebUI."""
import httpx
import json
from typing import Optional, List, Dict, Any
from config import settings
from sqlalchemy.orm import Session
from models import ApiKey
import bcrypt


class LLMService:
    """LLM service for summarization and action item extraction."""
    
    def __init__(self):
        """Initialize LLM service with OpenWebUI endpoint."""
        # Ensure the URL uses the correct OpenWebUI endpoint format
        base_url = settings.openwebui_url
        # Fix common URL issues: remove /v1 if present, ensure /api/chat/completions
        if '/api/v1/chat/completions' in base_url:
            base_url = base_url.replace('/api/v1/chat/completions', '/api/chat/completions')
        elif not base_url.endswith('/api/chat/completions'):
            # If URL doesn't end with the endpoint, append it
            base_url = base_url.rstrip('/') + '/api/chat/completions'
        self.base_url = base_url
        self.model = settings.openwebui_model
        self.temperature = settings.openwebui_temperature
        self.max_tokens = settings.openwebui_max_tokens
    
    def _get_api_key(self, db: Session, api_key_id: Optional[int] = None, profile_id: Optional[int] = None) -> Optional[str]:
        """Retrieve and verify API key from environment variable or database."""
        # First, check environment variable (takes precedence)
        if settings.openwebui_api_key:
            return settings.openwebui_api_key
        
        # Fall back to database lookup (if needed in future)
        query = db.query(ApiKey).filter(ApiKey.is_active == True)
        
        if api_key_id:
            query = query.filter(ApiKey.id == api_key_id)
        elif profile_id:
            query = query.filter(ApiKey.profile_id == profile_id)
        else:
            # Get first active API key
            api_key = query.first()
            if api_key:
                # Note: We can't decrypt hashed keys, so we need to store them differently
                # For now, this is a limitation - API keys should be stored encrypted, not hashed
                # This is a TODO for proper implementation
                return None
        
        api_key = query.first()
        if not api_key:
            return None
        
        # Since we hash API keys, we can't retrieve them
        # In production, you'd want to use encryption instead of hashing for API keys
        # For now, return None to indicate no key available
        return None
    
    async def _call_llm(
        self,
        prompt: str,
        api_key: Optional[str] = None
    ) -> str:
        """Call LLM via OpenWebUI endpoint."""
        headers = {
            "Content-Type": "application/json"
        }
        
        # OpenWebUI requires Bearer token authentication
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif settings.openwebui_api_key:
            # Fallback to environment variable if no key provided
            headers["Authorization"] = f"Bearer {settings.openwebui_api_key}"
        
        # OpenWebUI uses OpenAI-compatible format
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                # OpenWebUI returns OpenAI-compatible format
                if isinstance(result, dict):
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0].get("message", {}).get("content", "")
                    elif "message" in result:
                        return result["message"].get("content", "")
                    elif "response" in result:
                        return result["response"]
                    elif "text" in result:
                        return result["text"]
                elif isinstance(result, str):
                    return result
                
                return str(result)
            except httpx.HTTPStatusError as e:
                error_detail = f"HTTP {e.response.status_code}"
                try:
                    error_body = e.response.json()
                    if "detail" in error_body:
                        error_detail = error_body["detail"]
                    elif "message" in error_body:
                        error_detail = error_body["message"]
                except:
                    error_detail = e.response.text or error_detail
                raise ValueError(f"LLM API call failed: {error_detail}")
            except httpx.HTTPError as e:
                raise ValueError(f"LLM API call failed: {e}")
    
    async def generate_summary(
        self,
        transcript_text: str,
        db: Session,
        api_key_id: Optional[int] = None,
        profile_id: Optional[int] = None
    ) -> str:
        """Generate summary from transcript."""
        prompt = f"""Please provide a concise summary of the following transcript. 
Focus on the main points, key topics discussed, and important conclusions.

Transcript:
{transcript_text}

Summary:"""
        
        # Note: API key retrieval is limited due to hashing
        # In production, use encryption for API keys that need to be retrieved
        api_key = self._get_api_key(db, api_key_id, profile_id)
        
        summary = await self._call_llm(prompt, api_key)
        return summary.strip()
    
    async def extract_action_items(
        self,
        transcript_text: str,
        db: Session,
        api_key_id: Optional[int] = None,
        profile_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Extract action items from transcript."""
        prompt = f"""Please extract action items from the following transcript. 
Return the results as a JSON array of objects, where each object has:
- "action": string describing the action
- "assignee": string with the person responsible (if mentioned, otherwise "Unassigned")
- "priority": string ("high", "medium", "low")
- "deadline": string with deadline if mentioned, otherwise null

Transcript:
{transcript_text}

Return only valid JSON array, no other text:"""
        
        api_key = self._get_api_key(db, api_key_id, profile_id)
        
        response = await self._call_llm(prompt, api_key)
        
        # Try to parse JSON response
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
            
            action_items = json.loads(response)
            if isinstance(action_items, list):
                return action_items
            else:
                return [action_items] if action_items else []
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract action items manually
            # This is a fallback - better to improve the prompt
            return [{"action": response, "assignee": "Unassigned", "priority": "medium", "deadline": None}]


def get_llm_service() -> LLMService:
    """Get LLM service instance."""
    return LLMService()
