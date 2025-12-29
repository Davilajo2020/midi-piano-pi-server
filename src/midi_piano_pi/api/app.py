"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..core.config import get_settings
from ..core.midi_controller import get_midi_controller
from .routes import catalog, files, piano, playback, status
from .websocket.piano_handler import piano_websocket_endpoint

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Connect to MIDI device
    logger.info("Starting MIDI Piano Pi...")
    midi = get_midi_controller()
    if midi.connect():
        logger.info("MIDI connected: %s", midi.device_name)
    else:
        logger.warning("Failed to connect to MIDI device on startup")

    yield

    # Shutdown: Disconnect MIDI
    logger.info("Shutting down MIDI Piano Pi...")
    midi.all_notes_off()
    midi.disconnect()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="MIDI Piano Pi",
        description="Network-enabled MIDI piano control",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware for local network access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for local network
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    app.include_router(status.router)
    app.include_router(piano.router)
    app.include_router(files.router)
    app.include_router(playback.router)
    app.include_router(catalog.router)

    # Register WebSocket endpoints
    @app.websocket("/ws/piano")
    async def websocket_piano(websocket: WebSocket):
        await piano_websocket_endpoint(websocket)

    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    # Mount static files for web UI (must be last to not override API routes)
    web_dir = Path(__file__).parent.parent.parent.parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="static")

    return app


# Create the application instance
app = create_app()
