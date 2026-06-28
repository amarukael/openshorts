"""
Ollama AI Provider for OpenShorts.

Uses Ollama local REST API (POST /api/generate).
No API key required — Ollama runs locally, completely free.
All methods use transcript-only mode — no video upload capability.
Prompts are intentionally simple and very explicit for local model capabilities.
"""
import os
import json
from typing import Optional

from ai_providers.base import AIProvider

# ── Prompt: Viral Clip Detection (Ollama version) ──────────────────────────
# Very direct and explicit — local models need clear, simple instructions.
# No XML tags, no complex formatting; just straightforward JSON-only output.
OLLAMA_VIRAL_PROMPT_TEMPLATE = """You are a video editor. Pick the 3-15 most viral moments from this transcript for TikTok/Instagram/YouTube Shorts.

Rules:
- Each clip: 15-60 seconds long
- Timestamps in absolute seconds (numbers only, e.g. 12.5)
- 0 <= start < end <= {video_duration}
- Order by viral potential (best first)
- Never cut mid-word

Video duration: {video_duration}s
Transcript: {transcript_text}
Word timestamps (w=word, s=start_sec, e=end_sec): {words_json}

Return ONLY valid JSON, no explanation. Schema:
{{
  "shorts": [
    {{
      "start": <number>,
      "end": <number>,
      "video_description_for_tiktok": "<description with CTA>",
      "video_description_for_instagram": "<description with CTA>",
      "video_title_for_youtube_short": "<title max 100 chars>",
      "viral_hook_text": "<hook text max 10 words same language as transcript>"
    }}
  ]
}}"""

# ── Prompt: FFmpeg Filter (Ollama version) ─────────────────────────────────
OLLAMA_FFMPEG_PROMPT_TEMPLATE = """You are an FFmpeg expert. Generate a video filtergraph based on this transcript.

Video: {duration}s, {fps}fps, {width}x{height}
Transcript: {transcript_text}

Add zoom and rotation effects at impactful speech moments. Keep {width}x{height} resolution.

Return ONLY valid JSON, no explanation. Schema:
{{
  "filter_complex": "<valid FFmpeg filter_complex string>"
}}"""

# ── Prompt: Effects Config (Ollama version) ────────────────────────────────
OLLAMA_EFFECTS_PROMPT_TEMPLATE = """You are a video effects designer. Generate Remotion effects config based on this transcript.

Video: {duration}s, {fps}fps, {width}x{height}
Transcript: {transcript_text}

Create dynamic segments with zoom and color effects timed to speech.

Return ONLY valid JSON, no explanation. Schema:
{{
  "segments": [
    {{
      "startFrame": <int>,
      "endFrame": <int>,
      "zoomLevel": <float 1.0-1.5>,
      "rotation": <float>,
      "zoomCenterX": <float 0.0-1.0>,
      "zoomCenterY": <float 0.0-1.0>,
      "brightnessMultiplier": <float>,
      "contrastMultiplier": <float>,
      "saturationMultiplier": <float>
    }}
  ]
}}"""


class OllamaProvider(AIProvider):
    """
    AI provider implementation using local Ollama server.

    No API key required. Runs completely locally and free.
    Requires Ollama to be running: `ollama serve`
    Default model: llama3.2 (override with OLLAMA_MODEL env var)
    """

    def __init__(self, api_key: str = None):
        # api_key is accepted for interface consistency but ignored — Ollama is local/free
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_MODEL", "llama3.2")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _generate(self, prompt: str, timeout: int = 120) -> str:
        """Send a prompt to Ollama and return the response text."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        try:
            response = httpx.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()["response"]
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running: ollama serve"
            )
        except httpx.TimeoutException:
            raise ConnectionError(
                f"Ollama request timed out after {timeout}s. "
                "Try a smaller/faster model or increase timeout."
            )

    # ── AIProvider interface ─────────────────────────────────────────────────

    def get_viral_clips(
        self,
        transcript_text: str,
        words_json: list,
        video_duration: float,
    ) -> dict:
        """Analyze transcript and return viral clip timestamps using local Ollama."""
        prompt = OLLAMA_VIRAL_PROMPT_TEMPLATE.format(
            transcript_text=transcript_text,
            words_json=json.dumps(words_json),
            video_duration=video_duration,
        )

        try:
            raw = self._generate(prompt)
            result = json.loads(raw)
            result["cost_analysis"] = None  # Local/free — no cost tracking
            return result
        except ConnectionError:
            raise
        except Exception as e:
            print(f"❌ Ollama viral clips error: {e}")
            return {"shorts": [], "cost_analysis": None, "error": str(e)}

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
        Generate FFmpeg filter_complex using transcript only.
        video_path is ignored — Ollama does not support video file input.
        """
        transcript_text = json.dumps(transcript) if transcript else "Not available."

        prompt = OLLAMA_FFMPEG_PROMPT_TEMPLATE.format(
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transcript_text=transcript_text,
        )

        try:
            raw = self._generate(prompt)
            result = json.loads(raw)
            result["success"] = True
            return result
        except ConnectionError:
            raise
        except Exception as e:
            print(f"❌ Ollama ffmpeg filter error: {e}")
            return {"filter_complex": "", "success": False, "error": str(e)}

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
        Generate Remotion effects config using transcript only.
        video_path is ignored — Ollama does not support video file input.
        """
        transcript_text = json.dumps(transcript) if transcript else "Not available."

        prompt = OLLAMA_EFFECTS_PROMPT_TEMPLATE.format(
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transcript_text=transcript_text,
        )

        try:
            raw = self._generate(prompt)
            result = json.loads(raw)
            result["success"] = True
            return result
        except ConnectionError:
            raise
        except Exception as e:
            print(f"❌ Ollama effects config error: {e}")
            return {"segments": [], "success": False, "error": str(e)}
