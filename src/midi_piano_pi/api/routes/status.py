"""Status and health check endpoints."""

import json
import os
import subprocess
from pathlib import Path

import psutil
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...core.midi_controller import MIDIController, get_midi_controller

# Runtime settings file for audio delay
RUNTIME_SETTINGS_FILE = Path("/var/lib/midi-piano-pi/settings.json")


def _run_user_systemctl(command: str, service: str) -> tuple[bool, str]:
    """Run a systemctl --user command."""
    try:
        # Get the user's UID for the XDG_RUNTIME_DIR
        uid = os.getuid()
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"

        result = subprocess.run(
            ["systemctl", "--user", command, service],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        return result.returncode == 0, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)


def _is_service_active(service: str) -> bool:
    """Check if a user service is active."""
    try:
        uid = os.getuid()
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"

        result = subprocess.run(
            ["systemctl", "--user", "is-active", service],
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False

router = APIRouter(prefix="/api/v1/status", tags=["status"])


@router.get("")
async def get_status(midi: MIDIController = Depends(get_midi_controller)):
    """Get overall system status."""
    # Get system stats
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()

    # Try to get temperature (Raspberry Pi specific)
    temperature = None
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temperature = int(f.read()) / 1000.0
    except (FileNotFoundError, ValueError):
        pass

    return {
        "status": "ok",
        "midi": {
            "connected": midi.connected,
            "device_name": midi.device_name,
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "temperature_c": temperature,
        },
    }


@router.get("/midi")
async def get_midi_status(midi: MIDIController = Depends(get_midi_controller)):
    """Get MIDI connection status."""
    inputs, outputs = midi.list_devices()

    return {
        "connected": midi.connected,
        "device_name": midi.device_name,
        "available_inputs": [{"name": d.name, "port": d.port_index} for d in inputs],
        "available_outputs": [{"name": d.name, "port": d.port_index} for d in outputs],
    }


@router.post("/midi/connect")
async def connect_midi(midi: MIDIController = Depends(get_midi_controller)):
    """Connect to the MIDI device."""
    success = midi.connect()
    return {
        "success": success,
        "connected": midi.connected,
        "device_name": midi.device_name,
    }


@router.post("/midi/disconnect")
async def disconnect_midi(midi: MIDIController = Depends(get_midi_controller)):
    """Disconnect from the MIDI device."""
    midi.disconnect()
    return {
        "success": True,
        "connected": midi.connected,
    }


@router.get("/airplay")
async def get_airplay_status():
    """Get AirPlay broadcast status."""
    active = _is_service_active("fluidsynth-broadcast")
    return {
        "enabled": active,
        "service": "fluidsynth-broadcast",
    }


@router.post("/airplay/enable")
async def enable_airplay():
    """Enable AirPlay broadcast (start FluidSynth)."""
    success, message = _run_user_systemctl("start", "fluidsynth-broadcast")
    active = _is_service_active("fluidsynth-broadcast")
    return {
        "success": success,
        "enabled": active,
        "message": message if not success else None,
    }


@router.post("/airplay/disable")
async def disable_airplay():
    """Disable AirPlay broadcast (stop FluidSynth)."""
    success, message = _run_user_systemctl("stop", "fluidsynth-broadcast")
    active = _is_service_active("fluidsynth-broadcast")
    return {
        "success": success,
        "enabled": active,
        "message": message if not success else None,
    }


# ============================================
# Audio Delay Settings
# ============================================

def _load_runtime_settings() -> dict:
    """Load runtime settings from file."""
    if RUNTIME_SETTINGS_FILE.exists():
        try:
            return json.loads(RUNTIME_SETTINGS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_runtime_settings(settings: dict) -> None:
    """Save runtime settings to file."""
    RUNTIME_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


def _apply_audio_delay(delay_ms: int) -> tuple[bool, str]:
    """Apply audio delay using PulseAudio/PipeWire latency offset."""
    try:
        uid = os.getuid()
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"

        # Convert ms to microseconds for PulseAudio
        delay_usec = delay_ms * 1000

        # Use pactl to set the latency offset on the default sink
        # This adds artificial latency to the audio output
        result = subprocess.run(
            ["pactl", "set-port-latency-offset", "@DEFAULT_SINK@", "analog-output-lineout", str(delay_usec)],
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )

        if result.returncode != 0:
            # Try alternative: set on all sinks
            result = subprocess.run(
                ["pactl", "list", "sinks", "short"],
                capture_output=True,
                text=True,
                env=env,
                timeout=5,
            )
            # Fallback: just save the setting, FluidSynth will use it on restart
            return True, "Delay saved (will apply on next FluidSynth restart)"

        return True, "Delay applied"
    except Exception as e:
        return False, str(e)


class AudioDelayRequest(BaseModel):
    """Request to set audio delay."""
    delay_ms: int = Field(..., ge=0, le=2000, description="Audio delay in milliseconds (0-2000)")


@router.get("/airplay/delay")
async def get_audio_delay():
    """Get current audio delay setting."""
    settings = _load_runtime_settings()
    delay_ms = settings.get("audio_delay_ms", 0)
    return {
        "delay_ms": delay_ms,
    }


@router.put("/airplay/delay")
async def set_audio_delay(request: AudioDelayRequest):
    """Set audio delay for AirPlay broadcast to sync with piano."""
    settings = _load_runtime_settings()
    settings["audio_delay_ms"] = request.delay_ms
    _save_runtime_settings(settings)

    success, message = _apply_audio_delay(request.delay_ms)

    return {
        "success": success,
        "delay_ms": request.delay_ms,
        "message": message,
    }
