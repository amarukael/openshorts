"""
Gemini AI Provider for OpenShorts.

Wraps existing Gemini logic from main.py and editor.py into the AIProvider interface.
Uses Gemini File API for video upload (proprietary — not available in other providers).
"""
import os
import json
import re
import time
from typing import Optional
from google import genai
from google.genai import types
from ai_providers.base import AIProvider


# ── Prompt: Viral Clip Detection (Gemini) ──────────────────────────────────
# NOTE: This prompt is Gemini-specific. It relies on Gemini's multimodal
# understanding and proprietary JSON output behavior. Do NOT use for other providers.
GEMINI_VIRAL_PROMPT_TEMPLATE = """
You are a senior short-form video editor. Read the ENTIRE transcript and word-level timestamps to choose the 3–15 MOST VIRAL moments for TikTok/IG Reels/YouTube Shorts. Each clip must be between 15 and 60 seconds long.

⚠️ FFMPEG TIME CONTRACT — STRICT REQUIREMENTS:
- Return timestamps in ABSOLUTE SECONDS from the start of the video (usable in: ffmpeg -ss <start> -to <end> -i <input> ...).
- Only NUMBERS with decimal point, up to 3 decimals (examples: 0, 1.250, 17.350).
- Ensure 0 ≤ start < end ≤ VIDEO_DURATION_SECONDS.
- Each clip between 15 and 60 s (inclusive).
- Prefer starting 0.2–0.4 s BEFORE the hook and ending 0.2–0.4 s AFTER the payoff.
- Use silence moments for natural cuts; never cut in the middle of a word or phrase.
- STRICTLY FORBIDDEN to use time formats other than absolute seconds.

VIDEO_DURATION_SECONDS: {video_duration}

TRANSCRIPT_TEXT (raw):
{transcript_text}

WORDS_JSON (array of {{w, s, e}} where s/e are seconds):
{words_json}

STRICT EXCLUSIONS:
- No generic intros/outros or purely sponsorship segments unless they contain the hook.
- No clips < 15 s or > 60 s.

OUTPUT — RETURN ONLY VALID JSON (no markdown, no comments). Order clips by predicted performance (best to worst). In the descriptions, ALWAYS include a CTA like "Follow me and comment X and I'll send you the workflow" (especially if discussing an n8n workflow):
{{
  "shorts": [
    {{
      "start": <number in seconds, e.g., 12.340>,
      "end": <number in seconds, e.g., 37.900>,
      "video_description_for_tiktok": "<description for TikTok oriented to get views>",
      "video_description_for_instagram": "<description for Instagram oriented to get views>",
      "video_title_for_youtube_short": "<title for YouTube Short oriented to get views 100 chars max>",
      "viral_hook_text": "<SHORT punchy text overlay (max 10 words). MUST BE IN THE SAME LANGUAGE AS THE VIDEO TRANSCRIPT. Examples: 'POV: You realized...', 'Did you know?', 'Stop doing this!'>"
    }}
  ]
}}
"""


class GeminiProvider(AIProvider):
    """
    AI provider implementation using Google Gemini.

    Unique capabilities vs other providers:
    - Gemini File API: can upload video files directly for visual analysis
    - get_ffmpeg_filter() and get_effects_config() use actual video content
    - Google Search grounding available (used in saasshorts.py)
    """

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # ── Viral Clip Detection ───────────────────────────────────────────────

    def get_viral_clips(
        self,
        transcript_text: str,
        words_json: list,
        video_duration: float,
    ) -> dict:
        """
        Analyze transcript with Gemini and return viral clip timestamps.
        Ported from main.py get_viral_clips().
        """
        print(f"🤖  Analyzing with Gemini ({self.model_name})...")

        prompt = GEMINI_VIRAL_PROMPT_TEMPLATE.format(
            video_duration=video_duration,
            transcript_text=json.dumps(transcript_text),
            words_json=json.dumps(words_json),
        )

        cost_analysis = None
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            # Cost calculation (Gemini 2.5 Flash pricing)
            try:
                usage = response.usage_metadata
                if usage:
                    input_price_per_million = 0.10
                    output_price_per_million = 0.40
                    prompt_tokens = usage.prompt_token_count
                    output_tokens = usage.candidates_token_count
                    input_cost = (prompt_tokens / 1_000_000) * input_price_per_million
                    output_cost = (output_tokens / 1_000_000) * output_price_per_million
                    total_cost = input_cost + output_cost
                    cost_analysis = {
                        "input_tokens": prompt_tokens,
                        "output_tokens": output_tokens,
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "total_cost": total_cost,
                        "model": self.model_name,
                    }
                    print(f"💰 Token Usage ({self.model_name}):")
                    print(f"   - Input Tokens: {prompt_tokens} (${input_cost:.6f})")
                    print(f"   - Output Tokens: {output_tokens} (${output_cost:.6f})")
                    print(f"   - Total Estimated Cost: ${total_cost:.6f}")
            except Exception as e:
                print(f"⚠️ Could not calculate cost: {e}")

            # Strip markdown fences if present
            text = response.text
            text = re.sub(r"```(?:json)?\s*\n?", "", text).strip().rstrip("```").strip()

            result_json = json.loads(text)
            if cost_analysis:
                result_json["cost_analysis"] = cost_analysis
            return result_json

        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            return None

    # ── Video Upload (Gemini File API) ─────────────────────────────────────

    def upload_video(self, video_path: str):
        """
        Upload video to Gemini File API and wait for ACTIVE state.
        Ported from editor.py VideoEditor.upload_video().
        This is a Gemini-specific capability — not available in other providers.
        """
        print(f"📤 Uploading {video_path} to Gemini...")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        try:
            file_upload = self.client.files.upload(file=video_path)
        except Exception as e:
            print(f"❌ Gemini Upload Error: {e}")
            raise e

        print("⏳ Waiting for video processing by Gemini...")
        while True:
            file_info = self.client.files.get(name=file_upload.name)
            if file_info.state == "ACTIVE":
                print("✅ Video processed and ready.")
                return file_upload
            elif file_info.state == "FAILED":
                raise Exception("Video processing failed by Gemini.")
            time.sleep(2)

    # ── FFmpeg Filter Generation ───────────────────────────────────────────

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
        Ask Gemini for an FFmpeg filter string. Uses video upload if video_path provided.
        Ported from editor.py VideoEditor.get_ffmpeg_filter().
        """
        transcript_text = json.dumps(transcript) if transcript else "Not available."

        prompt = f"""
        You are an expert FFmpeg video editor. Your task is to generate a complex video filter string to make a short video viral, BUT ONLY apply effects where they make sense contextually.

        Video Duration: {duration} seconds.
        Video FPS: {fps}
        Video Resolution (MUST KEEP EXACT): {width}x{height}

        TRANSCRIPT (Context of what is being said):
        {transcript_text}

        Goal: Enhance the video with dynamic zooms, cuts (simulated with punch-ins), and visual effects to increase retention, but DO NOT overdo it. Random effects are bad. Contextual effects are good.

        Instructions:
        1. ANALYZE THE VIDEO AND TRANSCRIPT: Understand the mood, the pacing, and the key moments.
        2. APPLY EFFECTS ONLY WHEN RELEVANT:
           - Use "punch-in" zooms (zoompan) to emphasize key points, jokes, or dramatic moments in the speech.
           - slow zooms to face when the speaker is speaking
           - Use visual effects (contrast, saturation, sharpness) to highlight mood changes or specific segments.
           - If nothing significant is happening, keep it simple. It is BETTER to have no effect than a random/distracting one.
           - Avoid constant motion if the speaker is delivering a serious or steady message.
        3. Create a single valid FFmpeg filter complex string (for the -vf flag).
        4. Use filters like `zoompan`, `eq` (contrast), `hue` (saturation/bw), `unsharp`.
        5. Pacing: Align effects with the rhythm of the speech (from transcript) or visual action.
        6. CRITICAL SYNTAX RULES:
           - DO NOT use comparison operators like `<`, `>`, `<=`, `>=` anywhere.
           - USE FFmpeg expression FUNCTIONS: `between(x,a,b)`, `lt(x,y)`, `lte(x,y)`, `gt(x,y)`, `gte(x,y)`, `if(cond,then,else)`
           - Always wrap expression values in single quotes: `z='...'`, `x='...'`, `y='...'`, `enable='...'`.
           - FOR `zoompan`: prefer `on` (output frame index); convert seconds to frames: frame = seconds * {fps}
           - Use `between(on, startFrame, endFrame)` for segmenting.

        IMPORTANT: Return ONLY a valid JSON object. No markdown. No comments:
        {{"filter_complex": "<raw FFmpeg filtergraph string>", "success": true}}
        """

        try:
            if video_path and os.path.exists(video_path):
                video_file = self.upload_video(video_path)
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[video_file, prompt],
                )
            else:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )

            text = response.text
            text = re.sub(r"```(?:json)?\s*\n?", "", text).strip().rstrip("```").strip()
            result = json.loads(text)
            result["success"] = True
            return result
        except Exception as e:
            print(f"❌ Gemini FFmpeg filter error: {e}")
            return {"filter_complex": "", "success": False, "error": str(e)}

    # ── Effects Config Generation ──────────────────────────────────────────

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
        Ask Gemini for a Remotion effects config JSON. Uses video upload if video_path provided.
        Ported from editor.py VideoEditor.get_effects_config().
        """
        transcript_text = json.dumps(transcript) if transcript else "Not available."

        prompt = f"""
        You are a professional video effects artist. Generate a Remotion effects configuration for a {duration}-second viral short video.

        Video FPS: {fps}
        Video Resolution: {width}x{height}
        Zoom range allowed: 0.8-1.3.

        TRANSCRIPT (what is being said):
        {transcript_text}

        Instructions:
        1. ANALYZE the video content and transcript to understand mood, pacing, and key moments.
        2. Apply CONTEXTUAL effects aligned with speech and action:
           - Use slow, subtle zooms toward the speaker's face during speaking moments.
           - Emphasize key moments, punchlines, or dramatic beats with slightly stronger zoom or contrast.
           - Keep transitions smooth — avoid jarring jumps between segments.
           - If nothing significant is happening, keep values at defaults (zoom 1.0, all multipliers 1.0).
        3. Segments MUST cover the entire video duration from 0 to {duration} seconds with no gaps.
        4. Prefer fewer, longer segments with gradual changes over many rapid short segments.
        5. Output ONLY valid JSON, no explanations.

        Output format:
        {{
            "segments": [
                {{
                    "startSec": 0,
                    "endSec": 3.5,
                    "zoom": 1.0,
                    "zoomCenterX": 0.5,
                    "zoomCenterY": 0.5,
                    "brightnessMultiplier": 1.0,
                    "contrastMultiplier": 1.0,
                    "saturationMultiplier": 1.0
                }}
            ]
        }}
        """

        try:
            if video_path and os.path.exists(video_path):
                video_file = self.upload_video(video_path)
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[video_file, prompt],
                )
            else:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )

            text = response.text
            text = re.sub(r"```(?:json)?\s*\n?", "", text).strip().rstrip("```").strip()
            result = json.loads(text)
            result["success"] = True
            return result
        except Exception as e:
            print(f"❌ Gemini effects config error: {e}")
            return {"segments": [], "success": False, "error": str(e)}
