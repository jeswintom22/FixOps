# FixOps IQ Streamlit UI

This folder contains the hackathon-ready Streamlit dashboard for FixOps IQ.

## Files

- `app.py`: main Streamlit application
- `api.py`: reusable API client helpers for the FastAPI backend
- `config.py`: environment-based API URL loading
- `formatters.py`: report parsing helpers for evidence and remediation sections

## Environment

Set the backend URL with:

```powershell
$env:FIXOPS_API_URL="http://127.0.0.1:8000"
```

## Run

Start the FastAPI backend first, then launch Streamlit:

```powershell
streamlit run ui/app.py
```

The UI uses the existing API flow:

1. `POST /incidents`
2. `POST /investigate`
3. `GET /reports/{id}`
