# Suggested Commands

## Full Stack (Docker — recommended)
```bash
docker compose up --build        # Build and run entire stack
docker compose up                # Run without rebuild
docker compose down              # Stop all services
```
- Backend: http://localhost:8000
- Frontend: http://localhost:5175

## Backend Only (Python)
```bash
cd /home/amaru/hdd/repository/github/openshorts
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
uvicorn app:app --host 0.0.0.0 --port 8000 --reload  # dev with auto-reload
```

## Frontend Only (dashboard)
```bash
cd /home/amaru/hdd/repository/github/openshorts/dashboard
npm install
npm run dev        # Dev server HMR → http://localhost:5173
npm run build      # Production build → dist/
npm run preview    # Preview production build
npm run lint       # ESLint strict (--max-warnings 0)
```

## Render Service
```bash
cd /home/amaru/hdd/repository/github/openshorts/render-service
npm install
npm run dev        # tsx watch src/server.ts
npm run build      # tsc → dist/
npm start          # node dist/server.js
```

## Git
```bash
# Check upstream for updates
git remote add upstream https://github.com/mutonby/openshorts.git
git fetch upstream
git merge upstream/main
```

## Environment Setup
```bash
cp .env.example .env
# Edit .env with AWS credentials if needed
# API keys (Gemini, ElevenLabs, Upload-Post) are set in browser Settings UI, not .env
```
