# Task Completion

## After Backend Changes (Python)
```bash
# 1. Syntax check
cd /home/amaru/hdd/repository/github/openshorts
python -m py_compile app.py main.py editor.py hooks.py subtitles.py translate.py s3_uploader.py saasshorts.py thumbnail.py

# 2. Import check (catches missing deps)
python -c "import app"

# 3. (Optional) Run with reload to verify startup
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## After Frontend Changes (dashboard)
```bash
cd /home/amaru/hdd/repository/github/openshorts/dashboard

# 1. Lint (strict — must be 0 warnings)
npm run lint

# 2. Build check
npm run build
```

## After Render Service Changes
```bash
cd /home/amaru/hdd/repository/github/openshorts/render-service

# 1. TypeScript check
npm run build
```

## Full Stack Verification
```bash
cd /home/amaru/hdd/repository/github/openshorts
docker compose up --build
# Check: backend http://localhost:8000, frontend http://localhost:5175
```

## Before Committing
- No hardcoded kredensial akses (Gemini, ElevenLabs, AWS, Upload-Post)
- `.env` not committed (check `.gitignore`)
- ESLint passes for dashboard: `npm run lint`
- Python files compile: `python -m py_compile <file>`
