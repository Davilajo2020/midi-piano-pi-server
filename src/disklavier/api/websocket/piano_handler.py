"""WebSocket handler for real-time piano control."""

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from ...core.midi_controller import MIDIController, get_midi_controller

logger = logging.getLogger(__name__)


class PianoWebSocketHandler:
    """Handles WebSocket connections for real-time piano control."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._midi: Optional[MIDIController] = None

    @property
    def midi(self) -> MIDIController:
        """Get the MIDI controller instance."""
        if self._midi is None:
            self._midi = get_midi_controller()
        return self._midi

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

        # Ensure MIDI is connected
        if not self.midi.connected:
            self.midi.connect()

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "midi_device": self.midi.device_name,
            "midi_connected": self.midi.connected,
        })

        logger.info("WebSocket client connected. Total: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def handle_message(self, websocket: WebSocket, data: dict) -> None:
        """Handle an incoming WebSocket message."""
        msg_type = data.get("type")

        if msg_type == "ping":
            await websocket.send_json({
                "type": "pong",
                "timestamp": time.time(),
            })
            return

        if msg_type == "note_on":
            note = data.get("note", 60)
            velocity = data.get("velocity", 100)
            channel = data.get("channel")

            success = self.midi.note_on(note, velocity, channel)
            await websocket.send_json({
                "type": "note_sent",
                "note": note,
                "velocity": velocity,
                "success": success,
                "timestamp": time.time(),
            })

        elif msg_type == "note_off":
            note = data.get("note", 60)
            channel = data.get("channel")

            success = self.midi.note_off(note, channel)
            await websocket.send_json({
                "type": "note_sent",
                "note": note,
                "velocity": 0,
                "success": success,
                "timestamp": time.time(),
            })

        elif msg_type == "control_change":
            control = data.get("control", 64)
            value = data.get("value", 0)
            channel = data.get("channel")

            success = self.midi.control_change(control, value, channel)
            await websocket.send_json({
                "type": "control_sent",
                "control": control,
                "value": value,
                "success": success,
                "timestamp": time.time(),
            })

        elif msg_type == "sustain":
            on = data.get("on", False)
            channel = data.get("channel")

            success = self.midi.sustain_pedal(on, channel)
            await websocket.send_json({
                "type": "sustain_sent",
                "on": on,
                "success": success,
                "timestamp": time.time(),
            })

        elif msg_type == "panic":
            success = self.midi.all_notes_off()
            await websocket.send_json({
                "type": "panic_sent",
                "success": success,
                "timestamp": time.time(),
            })

        else:
            await websocket.send_json({
                "type": "error",
                "code": "UNKNOWN_MESSAGE_TYPE",
                "message": f"Unknown message type: {msg_type}",
            })


# Global handler instance
piano_handler = PianoWebSocketHandler()


async def piano_websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for piano control."""
    await piano_handler.connect(websocket)

    try:
        while True:
            try:
                data = await websocket.receive_json()
                await piano_handler.handle_message(websocket, data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "code": "INVALID_JSON",
                    "message": "Invalid JSON message",
                })
    except WebSocketDisconnect:
        piano_handler.disconnect(websocket)
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
        piano_handler.disconnect(websocket)
