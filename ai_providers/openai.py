"""
OpenAI AI Provider for OpenShorts.

Uses OpenAI ChatCompletion API (gpt-4o / gpt-4o-mini).
All methods use transcript-only mode — no video upload capability.
Prompts are intentionally different from GeminiProvider.
"""
import os
import json
import re
from typing import Optional
from ai_providers.base import AIProvider


# ── Prompt: Viral Clip Detection (OpenAI version) ──────────────────────────
# NOTE: This prompt is different from GEMINI_VIRAL_PROMPT_TEMPLATE:
# - No Gemini-specific markdown fence stripping instructions
# - No "FFMPEG TIME CONTRACT" branding — plain rules instead
# - Uses response_format=json_object so no need for JSON-only warnings
# - Simpler, direct instructions suited for GPT's instruction-following style
OPENAI_VIRAL_PROMPT_TEMPLATE = """You are a short-form video editor expert. Analyze this transcript and select the 3–15 most viral moments for TikTok/Instagram Reels/YouTube Shorts.

Rules:
- Each clip must be 15–60 seconds long
- Timestamps in absolute seconds from video start (decimal OK, e.g. 12.5)
- Ensure 0 ≤ start < end ≤ {video_duration}
- Order clips by predicted viral performance (best first)
- Start 0.2–0.4s before the hook, end 0.2–0.4s after the payoff
- Cut only at natural pauses — never mid-word or mid-sentence
- Avoid generic intros/outros and pure sponsorship segments

Video duration: {video_duration}s
Transcript: {transcript_text}
Word timestamps (JSON array of objects with w=word, s=start, e=end): {words_json}

Return a JSON object with this exact structure:
{{
  "shorts": [
    {{
      "start": <seconds as number>,
      "end": <seconds as number>,
      "video_description_for_tiktok": "<TikTok description with CTA — e.g. Follow + comment to get the workflow>",
      "video_description_for_instagram": "<Instagram description with CTA>",
      "video_title_for_youtube_short": "<YouTube title, max 100 chars>",
      "viral_hook_text": "<hook text overlay, max 10 words, SAME LANGUAGE as transcript>"
    }}
  ]
}}"""


# ── Prompt: FFmpeg Filter (OpenAI transcript-only version) ─────────────────
# Different from Gemini version:
# - No video upload — explicitly states transcript-only context
# - Instructs model to INFER timing from speech patterns rather than visual analysis
# - Simpler effect guidelines (no FFmpeg-specific zoompan `on` variable tricks)
OPENAI_FFMPEG_PROMPT_TEMPLATE = """You are an FFmpeg expert generating a video effects filtergraph based on transcript context only (no video available).

Video specs: {duration}s duration, {fps}fps, {width}x{height} resolution (MUST keep exact resolution)
Transcript: {transcript_text}

Since you cannot see the video, infer effect timing from the transcript:
- Apply zoom effects at key speech moments (punchlines, revelations, emphasis words)
- Use slow zooms during emotional or important statements
- Use fast punch-ins for jokes or surprising moments
- Maximum 1 effect per 8–10 seconds to avoid overuse
- If transcript is unavailable, return a simple pass-through filter

FFmpeg syntax rules:
- Use `between(t,a,b)` instead of comparison operators
- Use `lt(t,x)`, `gt(t,x)` etc. for time comparisons
- Wrap all expression values in single quotes
- Resolution MUST remain {width}x{height} throughout

Return a JSON object:
{{"filter_complex": "<raw FFmpeg filtergraph string for -vf flag>", "success": true}}"""


# ── Prompt: Effects Config (OpenAI transcript-only version) ───────────────
# Different from Gemini version:
# - Transcript-only — no video visual analysis
# - Infer rhythm from speech patterns
# - Fewer segments, simpler transitions
OPENAI_EFFECTS_PROMPT_TEMPLATE = """You are a video effects expert generating a Remotion effects configuration based on transcript context only (no video available).

Video: {duration}s, {fps}fps, {width}x{height}
Transcript: {transcript_text}

Infer effect timing from speech patterns and emotional cues:
- Slow subtle zooms during steady speech
- Slightly stronger zoom at punchlines or key moments
- Default values (zoom 1.0, multipliers 1.0) when nothing notable is happening
- Segments MUST cover 0 to {duration}s with no gaps
- Prefer fewer longer segments over many short rapid ones
- Zoom range: 0.8–1.3 only

Return a JSON object:
{{
  "segments": [
    {{
      "startSec": <number>,
      "endSec": <number>,
      "zoom": <1.0>,
      "zoomCenterX": <0.5>,
      "zoomCenterY": <0.5>,
      "brightnessMultiplier": <1.0>,
      "contrastMultiplier": <1.0>,
      "saturationMultiplier": <1.0>
    }}
  ],
  "success": true
}}"""


class OpenAIProvider(AIProvider):
    """
    AI provider implementation using OpenAI ChatCompletion API.

    Key differences from GeminiProvider:
    - No video upload — all methods use transcript-only mode
    - Uses response_format=json_object for reliable JSON output
    - Prompts are simpler and more direct (GPT instruction-following style)
    - Cost tracking uses OpenAI usage object (not usage_metadata)
    - No Google Search grounding support
    """

    def __init__(self, api_key: str):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError(
                "openai package required: pip install openai>=1.0.0\n"
                "Add to requirements.txt: openai>=1.0.0"
            )
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from response, stripping markdown fences if present."""
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"```(?:json)?\s*\n?", "", content).strip().rstrip("```").strip()
        return json.loads(content)

    def _log_cost(self, usage, label: str = "") -> dict:
        """Log OpenAI token usage and estimated cost."""
        if not usage:
            return {}
        # gpt-4o-mini pricing (as of 2025): $0.15/1M input, $0.60/1M output
        # gpt-4o pricing: $2.50/1M input, $10.00/1M output
        prices = {
            "gpt-4o-mini": (0.15, 0.60),
            "gpt-4o": (2.50, 10.00),
            "gpt-4o-2024-11-20": (2.50, 10.00),
        }
        in_price, out_price = prices.get(self.model, (2.50, 10.00))
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        input_cost = (input_tokens / 1_000_000) * in_price
        output_cost = (output_tokens / 1_000_000) * out_price
        total_cost = input_cost + output_cost

        cost_analysis = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "model": self.model,
        }
        tag = f" [{label}]" if label else ""
        print(f"💰 OpenAI Token Usage{tag} ({self.model}):")
        print(f"   - Input: {input_tokens} tokens (${input_cost:.6f})")
        print(f"   - Output: {output_tokens} tokens (${output_cost:.6f})")
        print(f"   - Total: ${total_cost:.6f}")
        return cost_analysis

    # ── Viral Clip Detection ───────────────────────────────────────────────

    def get_viral_clips(
        self,
        transcript_text: str,
        words_json: list,
        video_duration: float,
    ) -> dict:
        """
        Analyze transcript with OpenAI and return viral clip timestamps.
        Uses transcript-only analysis (no video).
        """
        print(f"🤖  Analyzing with OpenAI ({self.model})...")

        prompt = OPENAI_VIRAL_PROMPT_TEMPLATE.format(
            video_duration=video_duration,
            transcript_text=json.dumps(transcript_text) if isinstance(transcript_text, dict) else transcript_text,
            words_json=json.dumps(words_json),
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            cost_analysis = self._log_cost(response.usage, "viral_clips")
            result = self._parse_json(response.choices[0].message.content)
            if cost_analysis:
                result["cost_analysis"] = cost_analysis
            return result
        except Exception as e:
            print(f"❌ OpenAI viral clips error: {e}")
            return None

    # ── FFmpeg Filter Generation ───────────────────────────────────────────

    def get_ffmpeg_filter(
        self,
        duration: float,
        fps: float = 30,
        width: int = 1080,
        height: int = 1920,
        transcript: Optional[list] = None,
        video_path: Optional[str] = None,  # Ignored — OpenAI cannot receive video files
    ) -> dict:
        """
        Generate FFmpeg filter string using transcript only.
        video_path is ignored — OpenAI does not support video file input.
        """
        transcript_text = json.dumps(transcript) if transcript else "Not available."

        prompt = OPENAI_FFMPEG_PROMPT_TEMPLATE.format(
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transcript_text=transcript_text,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.5,
            )
            self._log_cost(response.usage, "ffmpeg_filter")
            result = self._parse_json(response.choices[0].message.content)
            result["success"] = True
            return result
        except Exception as e:
            print(f"❌ OpenAI FFmpeg filter error: {e}")
            return {"filter_complex": "", "success": False, "error": str(e)}

    # ── Effects Config Generation ──────────────────────────────────────────

    def get_effects_config(
        self,
        duration: float,
        fps: float = 30,
        width: int = 1080,
        height: int = 1920,
        transcript: Optional[list] = None,
        video_path: Optional[str] = None,  # Ignored — OpenAI cannot receive video files
    ) -> dict:
        """
        Generate Remotion effects config using transcript only.
        video_path is ignored — OpenAI does not support video file input.
        """
        transcript_text = json.dumps(transcript) if transcript else "Not available."

        prompt = OPENAI_EFFECTS_PROMPT_TEMPLATE.format(
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transcript_text=transcript_text,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.5,
            )
            self._log_cost(response.usage, "effects_config")
            result = self._parse_json(response.choices[0].message.content)
            result["success"] = True
            return result
        except Exception as e:
            print(f"❌ OpenAI effects config error: {e}")
            return {"segments": [], "success": False, "error": str(e)}
