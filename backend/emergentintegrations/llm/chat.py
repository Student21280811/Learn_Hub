"""
LLM Chat implementation using both OpenAI and Google Gemini.
"""

from dataclasses import dataclass
from typing import Optional
from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class UserMessage:
    """User message for chat"""
    text: str


class LlmChat:
    """LLM Chat implementation supporting OpenAI and Google Gemini"""
    
    def __init__(self, api_key: str, session_id: str, system_message: str = ""):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.model = "gemini-1.5-flash"  # Default model
        self.provider = "google"
    
    def with_model(self, provider: str, model: str) -> "LlmChat":
        """Set the model to use"""
        self.provider = provider
        # Map model names if necessary
        model_mapping = {
            "gpt-5-mini": "gpt-4o-mini",
            "gpt-5": "gpt-4o",
            "gemini-2.5-flash": "gemini-2.5-flash",
            "llama-70b": "llama-3.3-70b-versatile",
            "llama-8b": "llama3-8b-8192",
            "mixtral-8x7b": "mixtral-8x7b-32768"
        }
        self.model = model_mapping.get(model, model)
        return self
    
    async def send_message(self, message: UserMessage) -> str:
        """Send a message and get response"""
        try:
            if self.provider == "openai":
                import openai
                client = openai.AsyncOpenAI(api_key=self.api_key)
                
                messages = []
                if self.system_message:
                    messages.append({"role": "system", "content": self.system_message})
                messages.append({"role": "user", "content": message.text})
                
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                
                return response.choices[0].message.content
            
            elif self.provider == "google":
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                # Note: For Gemini 2.5, using the generativeai SDK
                model = genai.GenerativeModel(
                    model_name=self.model,
                    system_instruction=self.system_message if self.system_message else None
                )
                
                response = await model.generate_content_async(message.text)
                return response.text
            
            elif self.provider == "groq":
                # Groq is OpenAI-compatible
                client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url="https://api.groq.com/openai/v1"
                )
                
                messages = []
                if self.system_message:
                    messages.append({"role": "system", "content": self.system_message})
                messages.append({"role": "user", "content": message.text})
                
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                
                return response.choices[0].message.content
                
            else:
                return f"Unsupported provider: {self.provider}"
                
        except Exception as e:
            return f"AI service temporarily unavailable: {str(e)}"
