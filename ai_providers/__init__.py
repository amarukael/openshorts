# AI Providers package for OpenShorts
# Supports: gemini, openai, anthropic, ollama
#
# Imports are lazy (done inside each factory function in ai_config.py)
# to avoid requiring all provider SDKs at import time.
# Import specific providers only when needed:
#   from ai_providers.gemini import GeminiProvider
#   from ai_providers.openai import OpenAIProvider
#   from ai_providers.anthropic import AnthropicProvider
#   from ai_providers.ollama import OllamaProvider

from ai_providers.base import AIProvider

__all__ = [
    "AIProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
]
