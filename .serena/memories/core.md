# Core

## What is OpenShorts?
Free & open source AI video platform with 3 tools:
1. **Clip Generator** — turns long YouTube videos/uploads into viral 9:16 shorts (TikTok, Reels, YT Shorts)
2. **AI Shorts (UGC)** — generates marketing videos with AI actors (lip-sync, voiceover, b-roll, subtitles)
3. **YouTube Studio** — AI thumbnails, titles, descriptions, direct publishing

Forked from: `mutonby/openshorts` → `amarukael/openshorts`
Local path: `/home/amaru/hdd/repository/github/openshorts`

## Repository Structure
```
openshorts/
├── app.py                 # FastAPI server — async job queue + REST endpoints
├── main.py                # Core video processing (transcription, scene detect, crop, reframe)
├── editor.py              # Gemini AI → dynamic FFmpeg filter generation
├── hooks.py               # Hook text overlay with font rendering
├── subtitles.py           # SRT generation + FFmpeg subtitle burning
├── translate.py           # ElevenLabs dubbing API (30+ languages)
├── s3_uploader.py         # AWS S3 backup with caching
├── saasshorts.py          # AI Shorts / UGC video pipeline
├── thumbnail.py           # YouTube thumbnail generation
├── requirements.txt       # Python dependencies
├── Dockerfile             # Backend container
├── docker-compose.yml     # Full stack orchestration
├── .env.example           # Environment variable template
├── dashboard/             # React 18 + Vite frontend (JSX)
│   ├── src/App.jsx        # Main component with state management
│   └── src/components/   # UI components
├── render-service/        # Remotion render service (TypeScript + Express)
│   └── src/server.ts      # Express server wrapping @remotion/renderer
├── remotion/              # Remotion compositions for video rendering
└── fonts/                 # Custom font files
```

## Core Processing Pipeline (11 steps)
1. Ingest (yt-dlp or local upload)
2. Transcription (faster-whisper, word-level timestamps)
3. Scene Detection (PySceneDetect)
4. AI Analysis (Gemini 2.0 Flash — identifies 3-15 viral moments, 15-60s each)
5. FFmpeg Extraction (precise clip cutting)
6. AI Cropping (vertical reframe 9:16)
7. Effects/Subtitles (optional AI FFmpeg filters)
8. Hook Overlay (text overlays with styled fonts)
9. Voice Dubbing (optional ElevenLabs AI translation)
10. S3 Backup (silent background)
11. Social Distribution (Upload-Post API async)

## Key Classes
- `SmoothedCameraman` — stabilized camera with safe zone logic (prevents jitter)
- `SpeakerTracker` — prevents rapid speaker switching, handles occlusions

## Dual-Mode Video Reframing
- **TRACK Mode** (single subject): MediaPipe face detection + YOLOv8 fallback + "Heavy Tripod" stabilization
- **GENERAL Mode** (groups/landscapes): blurred background layout, preserves full width

## API Endpoints
| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/process` | Submit video for processing |
| GET | `/api/status/{job_id}` | Poll job status and logs |
| POST | `/api/edit` | Apply AI video effects |
| POST | `/api/subtitle` | Generate + apply subtitles |
| POST | `/api/hook` | Add text hook overlays |
| POST | `/api/translate` | AI voice dubbing |
| GET | `/api/translate/languages` | List supported languages |
| POST | `/api/social/post` | Post to social media |

## Concurrency Model
Async job queue with semaphore-based concurrency. `MAX_CONCURRENT_JOBS` env var (default: 5). Jobs auto-cleanup after 1 hour.

## Security Notes
- API keys (Gemini, ElevenLabs, Upload-Post) stored encrypted in browser localStorage, never server-side
- Sent via request headers only when needed
