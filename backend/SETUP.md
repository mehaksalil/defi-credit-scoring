# Backend Setup Guide

## Quick Setup

1. **Create and activate virtual environment:**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. **Install dependencies:**
```powershell
pip install -r requirements.txt
```

3. **Set up environment variables:**
```powershell
copy .env.example .env
# Edit .env and add your ETHERSCAN_API_KEY
```

4. **Train models (first time only):**
```powershell
python train_credit_model.py
```

5. **Run the server:**
```powershell
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000
API docs at http://localhost:8000/docs

## Troubleshooting

### If uvicorn is not recognized:
- Make sure the virtual environment is activated (you should see `(venv)` in your prompt)
- If activation doesn't work, try: `.\venv\Scripts\python.exe -m uvicorn app.main:app --reload`

### If you get permission errors:
- Run PowerShell as Administrator
- Or set execution policy: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
