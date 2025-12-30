"""
LLM Provider - Simplified interface for GPT-4o
"""
import os
from typing import List, Dict, Optional
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Base class for LLM providers"""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """Generate response from messages"""
        pass

    @abstractmethod
    def generate_json(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024
    ) -> dict:
        """Generate JSON response"""
        pass


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI GPT models"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1"
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found")
        self.model = model
        self.base_url = base_url

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """Generate text response"""
        import requests

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024
    ) -> dict:
        """Generate JSON response with structured output"""
        import requests
        import json

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            },
            timeout=60
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)


def create_provider(
    provider_type: str = "openai",
    **kwargs
) -> LLMProvider:
    """Factory function to create LLM provider"""
    if provider_type == "openai":
        return OpenAIProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider_type}")
