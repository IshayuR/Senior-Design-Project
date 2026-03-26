"""
Legacy entrypoint retained for convenience.

Local backend prototype now lives in:
    backend/app/main.py
Run it from the backend directory with:
    uvicorn app.main:app --reload
"""

if __name__ == "__main__":
    print("Use `uvicorn app.main:app --reload` from the `backend/` directory.")