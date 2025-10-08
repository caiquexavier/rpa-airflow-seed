"""FastAPI application entrypoint for rpa-api."""
import os
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from .env file
load_dotenv()

from .controllers.publish_controller import router as publish_router

app = FastAPI(title="rpa-api")

# Include routers
app.include_router(publish_router)


@app.get("/")
def root() -> Dict[str, str]:
    """Return service information."""
    return {"service": "rpa", "status": "ok"}


@app.get("/health")
def health() -> Dict[str, str]:
    """Return a simple health status response."""
    return {"status": "ok"}
