"""
LLM Provider for Llama-3.1-8B-Instruct
Supports both local inference and API-based inference (e.g., Ollama, vLLM)
"""
import json
from typing import List, Dict, Optional
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Base class for LLM providers"""

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate response from messages"""
        pass


class OllamaProvider(LLMProvider):
    """Provider for Ollama API (recommended for ease of use)"""

    def __init__(self, model_name: str = "llama3.1:8b-instruct-q4_K_M", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate response using Ollama API"""
        import requests

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Error calling Ollama API: {e}")


class HuggingFaceProvider(LLMProvider):
    """Provider for local Hugging Face transformers inference"""

    def __init__(self, model_name: str = "meta-llama/Llama-3.1-8B-Instruct", device: str = "auto"):
        """
        Initialize HuggingFace provider
        Note: Requires Hugging Face token for gated models like Llama
        """
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch

        print(f"Loading model {model_name}... This may take a few minutes.")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map=device,
            low_cpu_mem_usage=True
        )
        self.device = self.model.device
        print("Model loaded successfully!")

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate response using local HuggingFace model"""
        import torch

        # Format messages using chat template
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode only the new tokens
        response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )

        return response.strip()


class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs (vLLM, LM Studio, etc.)"""

    def __init__(self, base_url: str = "http://localhost:8000/v1", api_key: str = "dummy", model_name: str = "llama-3.1-8b-instruct"):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate response using OpenAI-compatible API"""
        import requests

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Error calling OpenAI-compatible API: {e}")


def create_llm_provider(provider_type: str = "ollama", **kwargs) -> LLMProvider:
    """
    Factory function to create LLM provider

    Args:
        provider_type: One of "ollama", "huggingface", "openai_compatible"
        **kwargs: Provider-specific arguments

    Returns:
        LLMProvider instance
    """
    providers = {
        "ollama": OllamaProvider,
        "huggingface": HuggingFaceProvider,
        "openai_compatible": OpenAICompatibleProvider
    }

    if provider_type not in providers:
        raise ValueError(f"Unknown provider type: {provider_type}. Choose from {list(providers.keys())}")

    return providers[provider_type](**kwargs)
