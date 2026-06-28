"""
AI Provider factory for OpenShorts.

Usage:
    from ai_config import get_ai_provider
    provider = get_ai_provider(api_key="...", provider_name="gemini")

Supported providers:
    - "gemini"    : Google Gemini (default) — uses Gemini File API for video upload
    - "openai"    : OpenAI ChatCompletion — transcript-only mode for ffmpeg/effects
    - "anthropic" : Anthropic Messages API — transcript-only mode (Phase 4, not yet impl)
    - "ollama"    : Local Ollama — transcript-only mode (Phase 5, not yet impl)
"""
import os
from typing import Optional
from ai_providers.base import AIProvider


def get_ai_provider(api_key: str, provider_name: Optional[str] = None) -> AIProvider:
    """
    Return the appropriate AIProvider instance.

    Args:
        api_key:       The kredensial akses for the provider (ignored for Ollama).
        provider_name: One of "gemini", "openai", "anthropic", "ollama".
                       Falls back to AI_PROVIDER env var, then "gemini".

    Returns:
        AIProvider instance ready to use.

    Raises:
        ValueError: If provider_name is not recognized.
        ImportError: If the required package for the provider is not installed.
    """
    if provider_name is None:
        provider_name = os.environ.get("AI_PROVIDER", "gemini").lower().strip()

    if provider_name == "gemini":
        from ai_providers.gemini import GeminiProvider
        return GeminiProvider(api_key)

    elif provider_name == "openai":
        from ai_providers.openai import OpenAIProvider
        return OpenAIProvider(api_key)

    elif provider_name == "anthropic":
        # Phase 4 — not yet implemented
        raise NotImplementedError(
            "Anthropic provider is not yet implemented. "
            "Use provider_name='gemini' or 'openai'."
        )

    elif provider_name == "ollama":
        # Phase 5 — not yet implemented
        raise NotImplementedError(
            "Ollama provider is not yet implemented. "
            "Use provider_name='gemini' or 'openai'."
        )

    else:
        raise ValueError(
            f"Unknown AI provider: '{provider_name}'. "
            f"Supported: gemini, openai. (anthropic, ollama coming soon)"
        )
