# Run backend (accepts connections from phone/emulator)
Set-Location $PSScriptRoot
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
