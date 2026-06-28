# Conventions

## Backend (Python)
- Python 3.11 — use f-strings, type hints where practical
- FastAPI async endpoints with `async def`
- Environment variables loaded via `python-dotenv` from `.env`
- API keys for Gemini/ElevenLabs come from request headers (client-side encrypted), not `.env`
- Job IDs generated as UUIDs; stored in in-memory dict (no DB)
- Async semaphore for concurrency control (`MAX_CONCURRENT_JOBS`)
- No test framework currently — verification via Docker + manual curl

## Frontend (dashboard — JSX)
- React 18 functional components with hooks
- **JSX only** — no TypeScript in dashboard (`.jsx`, `.js` extensions)
- Tailwind CSS 3.4 utility classes
- ESLint strict mode — zero warnings tolerance (`--max-warnings 0`)
- State management: React `useState`/`useEffect` (no Redux/Zustand)
- API calls: `fetch()` to backend (proxied via Vite config in dev)
- API keys stored encrypted in `localStorage`, sent via custom request headers

## Render Service (TypeScript)
- TypeScript strict mode, ESM (`"type": "module"`)
- Express 4 with Remotion renderer
- Zod for request validation

## File Naming
- Python: `snake_case.py`
- React components: `PascalCase.jsx`
- Utils/hooks: `camelCase.js`

## Environment Variables
- Server-side (`.env`): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_S3_PUBLIC_BUCKET`, `MAX_CONCURRENT_JOBS`, `YOUTUBE_COOKIES`
- Client-side (browser localStorage, encrypted): `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `UPLOAD_POST_API_KEY`
- Build-time: `VITE_API_URL` (production API URL override)

## Adding New Features
- Backend: add endpoint in `app.py`, logic in a new `feature.py` module
- Frontend: add component in `dashboard/src/components/`, wire in `App.jsx`
- Keep processing pipeline steps modular (separate files like `subtitles.py`, `translate.py`)
