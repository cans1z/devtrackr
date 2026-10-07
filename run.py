"""
Simple entry point to run the DevTrackr API.

Usage:
    python run.py
    uvicorn run:app --reload
    uvicorn src.main:app --reload

Environment:
    DEVTRACKR_HOST (default: 127.0.0.1), DEVTRACKR_PORT (default: 8000).
"""

from src.main import app  # noqa: F401 (exposed for uvicorn run:app)

if __name__ == "__main__":
    import os

    import uvicorn

    host = os.getenv("DEVTRACKR_HOST", "127.0.0.1")
    port = int(os.getenv("DEVTRACKR_PORT", "8000"))

    uvicorn.run("src.main:app", host=host, port=port, reload=True)
