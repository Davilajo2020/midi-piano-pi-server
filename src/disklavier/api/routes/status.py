"""Status and health check endpoints."""

import os
import subprocess

import psutil
from fastapi import APIRouter, Depends

from ...core.midi_controller import MIDIController, get_midi_controller


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
