"""
Anthropic AI Provider for OpenShorts.

Uses Anthropic Messages API (claude-3-5-haiku / claude-3-5-sonnet).
All methods use transcript-only mode — no video upload capability.
Prompts use XML tags style suited to Claude's instruction-following.
"""
import os
import json
from typing import Optional

try:
    from anthropic import Anthropic
except ImportError:
    raise ImportError("anthropic package required: pip install anthropic>=0.25.0")

from ai_providers.base import AIProvider

# ── Pricing (claude-3-5-haiku-20241022) ────────────────────────────────────
# Input:  $0.80 / 1M tokens
# Output: $4.00 / 1M tokens
_PRICE_INPUT_PER_M  = 0.80
_PRICE_OUTPUT_PER_M = 4.00

# ── Prompt: Viral Clip Detection (Anthropic version) ───────────────────────
# Uses XML tags — Claude is trained to handle structured XML prompts well.
# Output wrapped in <json> tags so we can extract reliably.
ANTHROPIC_VIRAL_PROMPT_TEMPLATE = """You are a senior short-form video editor. Analyze the transcript below and select the 3–15 MOST VIRAL moments for TikTok/Instagram Reels/YouTube Shorts.

Rules:
- Each clip must be 15–60 seconds long
- Timestamps in absolute seconds from video start (decimal OK, e.g. 12.5)
- Ensure 0 ≤ start < end ≤ {video_duration}
- Order clips by predicted viral performance (best first)
- Start 0.2–0.4s before the hook, end 0.2–0.4s after the payoff
- Cut only at natural pauses — never mid-word or mid-sentence
- Avoid generic intros/outros and pure sponsorship segments
- In descriptions, ALWAYS include a CTA (e.g. "Follow me and comment X and I'll send you the workflow")

<transcript>
{transcript_text}
</transcript>

<word_timestamps>
{words_json}
</word_timestamps>

Video duration: {video_duration}s

Output ONLY the JSON inside <json> tags. No explanation, no markdown, no text outside the tags.

<json>
{{
  "shorts": [
    {{
      "start": <seconds as number>,
      "end": <seconds as number>,
      "video_description_for_tiktok": "<TikTok description with CTA>",
      "video_description_for_instagram": "<Instagram description with CTA>",
      "video_title_for_youtube_short": "<YouTube title, max 100 chars>",
      "viral_hook_text": "<hook text overlay, max 10 words, SAME LANGUAGE as transcript>"
    }}
  ]
}}
</json>"""

# ── Prompt: FFmpeg Filter (Anthropic transcript-only version) ───────────────
ANTHROPIC_FFMPEG_PROMPT_TEMPLATE = """You are an FFmpeg expert. Generate a video effects filtergraph based on transcript context only (no video file available).

Video specs:
- Duration: {duration}s
- FPS: {fps}
- Resolution: {width}x{height} (MUST keep exact resolution)

<transcript>
{transcript_text}
</transcript>

Since you cannot see the video, infer effect timing from speech rhythm:
- Apply zoom effects at key speech moments (punchlines, revelations, emphasis words)
- Use slow zooms during calm narration, quick zooms at high-energy moments
- Add slight rotation for dynamic feel on impactful words
- All effects must preserve the exact {width}x{height} resolution

Output ONLY the JSON inside <json> tags.

<json>
{{
  "filter_complex": "<valid FFmpeg filter_complex string>"
}}
</json>"""

# ── Prompt: Effects Config (Anthropic transcript-only version) ─────────────
ANTHROPIC_EFFECTS_PROMPT_TEMPLATE = """You are a video effects designer. Generate a Remotion effects configuration JSON based on transcript context only (no video file available).

Video specs:
- Duration: {duration}s
- FPS: {fps}
- Resolution: {width}x{height}

<transcript>
{transcript_text}
</transcript>

Since you cannot see the video, infer effect timing from speech rhythm and content.
Create dynamic segments with zoom, rotation, and color grading effects timed to speech.

Output ONLY the JSON inside <json> tags.

<json>
{{
  "segments": [
    {{
      "startFrame": <int>,
      "endFrame": <int>,
      "zoomLevel": <float 1.0-1.5>,
      "rotation": <float degrees>,
      "zoomCenterX": <float 0.0-1.0>,
      "zoomCenterY": <float 0.0-1.0>,
      "brightnessMultiplier": <float>,
      "contrastMultiplier": <float>,
      "saturationMultiplier": <float>
    }}
  ]
}}
</json>"""


class AnthropicProvider(AIProvider):
    """
    AI provider implementation using Anthropic Claude.

    All methods use transcript-only mode — no video upload capability.
    Prompts use XML tag style suited to Claude's training.
    """

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _parse_json_from_tags(self, text: str) -> dict:
        """Extract JSON from between <json> and </json> tags, then parse it."""
        # Try to find content between <json> tags first
        start_tag = "<json>"
        end_tag = "</json>"
        start_idx = text.find(start_tag)
        end_idx = text.find(end_tag)

        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx + len(start_tag):end_idx].strip()
        else:
            # Fallback: try to parse the whole text as JSON (strip markdown fences)
            json_str = text.strip()
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1]) if len(lines) > 2 else json_str

        return json.loads(json_str)

    def _log_cost(self, usage, label: str = "") -> dict:
        """Calculate and log cost from Anthropic usage object."""
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)
        cost_usd = (input_tokens / 1_000_000 * _PRICE_INPUT_PER_M +
                    output_tokens / 1_000_000 * _PRICE_OUTPUT_PER_M)
        cost_info = {
            "model": self.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": round(cost_usd, 6),
        }
        if label:
            print(f"💰 Anthropic [{label}] {input_tokens}in + {output_tokens}out = ${cost_usd:.4f}")
        return cost_info

    # ── AIProvider interface ─────────────────────────────────────────────────

    def get_viral_clips(
        self,
        transcript_text: str,
        words_json: list,
        video_duration: float,
    ) -> dict:
        """Analyze transcript and return viral clip timestamps using Claude."""
        prompt = ANTHROPIC_VIRAL_PROMPT_TEMPLATE.format(
            transcript_text=transcript_text,
            words_json=json.dumps(words_json),
            video_duration=video_duration,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            result = self._parse_json_from_tags(text)
            result["cost_analysis"] = self._log_cost(response.usage, "viral_clips")
            return result
        except Exception as e:
            print(f"❌ Anthropic viral clips error: {e}")
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
        video_path is ignored — Anthropic does not support video file input.
        """
        transcript_text = json.dumps(transcript) if transcript else "Not available."

        prompt = ANTHROPIC_FFMPEG_PROMPT_TEMPLATE.format(
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transcript_text=transcript_text,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            result = self._parse_json_from_tags(text)
            result["success"] = True
            self._log_cost(response.usage, "ffmpeg_filter")
            return result
        except Exception as e:
            print(f"❌ Anthropic ffmpeg filter error: {e}")
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
        video_path is ignored — Anthropic does not support video file input.
        """
        transcript_text = json.dumps(transcript) if transcript else "Not available."

        prompt = ANTHROPIC_EFFECTS_PROMPT_TEMPLATE.format(
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transcript_text=transcript_text,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            result = self._parse_json_from_tags(text)
            result["success"] = True
            self._log_cost(response.usage, "effects_config")
            return result
        except Exception as e:
            print(f"❌ Anthropic effects config error: {e}")
            return {"segments": [], "success": False, "error": str(e)}
