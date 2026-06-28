"""
Abstract base class for all AI providers in OpenShorts.

Supported providers: gemini, openai, anthropic, ollama
"""
from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def get_viral_clips(
        self,
        transcript_text: str,
        words_json: list,
        video_duration: float,
    ) -> dict:
        """
        Analyze transcript and return viral clip timestamps.

        Returns:
            {
                "shorts": [
                    {
                        "start": float,
                        "end": float,
                        "video_description_for_tiktok": str,
                        "video_description_for_instagram": str,
                        "video_title_for_youtube_short": str,
                        "viral_hook_text": str,
                    }
                ],
                "cost_analysis": {...}  # optional, provider-dependent
            }
        """
        pass

    @abstractmethod
    def get_ffmpeg_filter(
        self,
        duration: float,
        fps: float = 30,
        width: int = 1080,
        height: int = 1920,
        transcript: Optional[list] = None,
        video_path: Optional[str] = None,
    ) -> dict:
        """
        Generate FFmpeg filter_complex string for a viral short.

        Note: video_path is only used by GeminiProvider (File API upload).
              All other providers use transcript-only mode and ignore video_path.

        Returns:
            {"filter_complex": str, "success": bool}
        """
        pass

    @abstractmethod
    def get_effects_config(
        self,
        duration: float,
        fps: float = 30,
        width: int = 1080,
        height: int = 1920,
        transcript: Optional[list] = None,
        video_path: Optional[str] = None,
    ) -> dict:
        """
        Generate Remotion effects configuration JSON for a viral short.

        Note: video_path is only used by GeminiProvider (File API upload).
              All other providers use transcript-only mode and ignore video_path.

        Returns:
            {"segments": [...], "success": bool}
        """
        pass
