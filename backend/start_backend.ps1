Set-Location "$PSScriptRoot"
& "D:\Tamper_Detection_crypto\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
