# Custom AI Provider Support Plan

**Created:** 2026-06-28
**Status:** Planning — not yet implemented

## Overview
Tambah abstraction layer agar OpenShorts bisa pakai provider AI selain Gemini (OpenAI, Anthropic, Ollama).

## Titik Integrasi AI (3 file utama)
| File | Fungsi | Catatan |
|------|--------|---------|
| `main.py` → `get_viral_clips()` | Viral moment detection dari transcript | Text-only, JSON output |
| `editor.py` → `get_ffmpeg_filter()` | Generate FFmpeg filter string | **Pakai Gemini File API (video upload)** |
| `editor.py` → `get_effects_config()` | Generate Remotion effects JSON | **Pakai Gemini File API (video upload)** |
| `saasshorts.py` | UGC pipeline (scraping, script gen) | Text-only + Google Search grounding |

**Tantangan utama:** `editor.py` pakai Gemini File API untuk upload video ke model — fitur proprietary. Provider lain tidak bisa terima video file → fallback ke transcript-only mode dengan prompt berbeda.

## Target Arsitektur

```
ai_providers/
├── __init__.py
├── base.py           # Abstract base class AIProvider
├── gemini.py         # Existing logic (dipindah dari main.py + editor.py)
├── openai.py         # ChatCompletion, text-only
├── anthropic.py      # Messages API, text-only
└── ollama.py         # Local, gratis, prompt paling simpel
```

**Config loader:** `ai_config.py` — baca `AI_PROVIDER` env var, return instance provider yang tepat.

## Perbedaan Prompt per Provider

| Aspek | Gemini | OpenAI | Anthropic | Ollama |
|-------|--------|--------|-----------|--------|
| Video input | File API (upload) | ❌ transcript-only | ❌ transcript-only | ❌ transcript-only |
| JSON output | Manual parse + markdown strip | `response_format=json_object` | Manual / `<json>` tag | Manual, explicit rules |
| FFmpeg filter | Visual analysis dari video | Infer dari transcript | Infer dari speech rhythm | Simpel, aturan eksplisit |
| Cost tracking | `usage_metadata` | `usage` object | `usage` object | ❌ N/A (local) |
| Grounding (saasshorts) | Google Search | ❌ skip | ❌ skip | ❌ skip |

## Rencana Phase

**Phase 1 — Abstract Base + Config**
- `ai_providers/base.py`: abstract class `AIProvider` dengan methods:
  - `get_viral_clips(transcript, duration) -> dict`
  - `get_ffmpeg_filter(video_or_none, duration, fps, width, height, transcript) -> dict`
  - `get_effects_config(video_or_none, duration, fps, width, height, transcript) -> dict`
- `ai_config.py`: factory function `get_ai_provider(api_key, provider_name) -> AIProvider`
- ENV: `AI_PROVIDER=gemini|openai|anthropic|ollama`

**Phase 2 — Gemini Provider (refactor existing)**
- Pindahkan `get_viral_clips()` dari `main.py` → `ai_providers/gemini.py`
- Pindahkan `VideoEditor` class dari `editor.py` → `ai_providers/gemini.py`
- Prompt Gemini TIDAK berubah — tetap pakai `GEMINI_PROMPT_TEMPLATE` yang ada
- Gemini tetap pakai File API untuk video

**Phase 3 — OpenAI Provider**
- `get_viral_clips()` → `gpt-4o` / `gpt-4o-mini`, prompt ringkas tanpa instruksi Gemini-specific
- `get_ffmpeg_filter()` → transcript-only fallback, prompt: "Based on this transcript only (no video available), generate FFmpeg filter..."
- `get_effects_config()` → sama, transcript-only
- Gunakan `response_format={"type": "json_object"}` untuk semua calls

**Phase 4 — Anthropic Provider**
- `get_viral_clips()` → `claude-3-5-haiku` / `claude-3-5-sonnet`
- Prompt split menjadi system + user message (format Anthropic)
- `get_ffmpeg_filter()` → transcript-only, prompt emphasize "infer visual rhythm from speech patterns"

**Phase 5 — Ollama Provider (local, gratis)**
- Target: `llama3.2`, `mistral`, `qwen2.5`
- Prompt paling simpel dan eksplisit — model lokal lebih lemah
- `get_ffmpeg_filter()` → transcript-only, prompt very direct: output JSON langsung
- Cocok untuk self-hosted / privacy use case

**Phase 6 — saasshorts.py refactor**
- Ganti `GEMINI_MODEL = "gemini-3-flash-preview"` hardcoded → pakai provider abstraction
- Google Search grounding → hanya tersedia di Gemini; provider lain skip / fallback web search via `httpx`

**Phase 7 — Frontend + .env**
- Tambah UI dropdown "AI Provider" di dashboard settings
- Update `.env.example`:
  ```
  AI_PROVIDER=gemini          # gemini | openai | anthropic | ollama
  GEMINI_API_KEY=***
  OPENAI_API_KEY=***
  ANTHROPIC_API_KEY=***
  OLLAMA_BASE_URL=http://localhost:11434
  OLLAMA_MODEL=llama3.2
  ```
- Kredensial tetap di browser localStorage, dikirim via header (sesuai existing pattern)

## Priority Implementasi
1. Phase 1 + 2 + 3 dulu (base → refactor Gemini → OpenAI) — paling banyak user pakai OpenAI
2. Phase 7 barengan supaya langsung bisa dicoba
3. Phase 4-6 menyusul
