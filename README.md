# ai-generalist-eci-results-site


Open two terminals from the project root:

Terminal 1 — FastAPI backend (port 8000):
cd /Users/sameermeher/Technical/Euron/AI_Generalist_1.0/ElectionResultsSite
APP_ENV=production /opt/homebrew/bin/python3.11 -m uvicorn api.main:app --port 8000 --reload

Terminal 2 — Streamlit dashboard (port 8502):

cd /Users/sameermeher/Technical/Euron/AI_Generalist_1.0/ElectionResultsSite
/opt/homebrew/bin/python3.11 -m streamlit run dashboard/app.py --server.port 8502

Then open:

Dashboard → http://localhost:8502
API docs → http://localhost:8000/docs
