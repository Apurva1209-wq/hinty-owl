# Hinty the Owl - AI Hint Buddy (Class 6-10)

## Run on Windows (easy)
1. Double-click  backend\start-backend.bat   (paste your Gemini / Groq key when asked)
2. Double-click  frontend\start-frontend.bat (browser opens at http://localhost:5500)

## Deploy on Vercel (two projects from one GitHub repo)
Backend : Root Directory = backend  -> add env vars GEMINI_API_KEY, GROQ_API_KEY, ALLOWED_ORIGIN
Frontend: Root Directory = frontend -> edit frontend/config.js with the backend URL first
