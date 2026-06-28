# Tech Stack

## Backend
- **Language:** Python 3.11
- **Framework:** FastAPI 0.136.1
- **Server:** Uvicorn 0.46.0
- **AI/ML:**
  - `google-genai==1.75.0` — Gemini 2.0 Flash (viral moment detection, effects, titles)
  - `faster-whisper==1.2.1` — speech transcription with word-level timestamps
  - `ultralytics==8.4.46` — YOLOv8 object/person detection
  - `mediapipe==0.10.14` — face detection for subject tracking
  - `torch==2.11.0` + `torchvision==0.26.0` — ML runtime
- **Video:** FFmpeg (system dependency, not in requirements.txt), `scenedetect==0.7`
- **Download:** `yt-dlp` (no version pin)
- **Storage:** `boto3==1.43.4` — AWS S3
- **HTTP:** `httpx==0.28.1`
- **Image:** `Pillow==12.2.0`
- **HTML parsing:** `beautifulsoup4==4.14.3`
- **Utils:** `python-dotenv==1.2.2`, `tqdm==4.67.3`, `python-multipart==0.0.27`

## Frontend (dashboard/)
- **Framework:** React 18.2
- **Build:** Vite 4.5.3
- **Language:** JSX (not TypeScript)
- **Styling:** Tailwind CSS 3.4.19 + PostCSS + Autoprefixer
- **Icons:** lucide-react 0.344.0
- **Video player:** Remotion 4.0.447 (`@remotion/player`, `@remotion/web-renderer`, `@remotion/media`)
- **Validation:** Zod 4.3.6
- **Linting:** ESLint 8.57.0 (strict, `--max-warnings 0`)
- Dev port: 5173 (HMR); proxied to backend at 8000 in Docker → 5175

## Render Service (render-service/)
- **Language:** TypeScript 5.4
- **Runtime:** Node.js (ESM)
- **Framework:** Express 4.21
- **Video rendering:** `@remotion/bundler` + `@remotion/renderer` 4.x
- **Build:** `tsc` → `dist/server.js`
- **Dev:** `tsx watch`

## Remotion Compositions (remotion/)
- Remotion 4.x compositions for AI Shorts video rendering

## Infrastructure
- **Containers:** Docker + Docker Compose
- **Storage:** AWS S3 (optional — clip backup + public gallery)
- **External APIs:** Google Gemini, ElevenLabs Dubbing, Upload-Post (social publishing)

## External Services (all optional except Gemini)
| Service | Purpose | Required |
|---------|---------|---------|
| Google Gemini | Viral detection, effects, titles | ✅ Yes (stored client-side) |
| ElevenLabs | AI voice dubbing | ❌ Optional |
| Upload-Post | TikTok/Instagram/YouTube publish | ❌ Optional |
| AWS S3 | Video backup + gallery | ❌ Optional |
