"""Piano control endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core.midi_controller import MIDIController, get_midi_controller

router = APIRouter(prefix="/api/v1/piano", tags=["piano"])


class NoteRequest(BaseModel):
    """Request to send a single note."""
    note: int = Field(..., ge=0, le=127, description="MIDI note number (0-127), 60 = Middle C")
    velocity: int = Field(100, ge=0, le=127, description="Note velocity (0-127)")
    channel: Optional[int] = Field(None, ge=0, le=15, description="MIDI channel (0-15)")


class NoteOffRequest(BaseModel):
    """Request to turn off a note."""
    note: int = Field(..., ge=0, le=127, description="MIDI note number (0-127)")
    channel: Optional[int] = Field(None, ge=0, le=15, description="MIDI channel (0-15)")


class ControlChangeRequest(BaseModel):
    """Request to send a control change."""
    control: int = Field(..., ge=0, le=127, description="Controller number (0-127)")
    value: int = Field(..., ge=0, le=127, description="Controller value (0-127)")
    channel: Optional[int] = Field(None, ge=0, le=15, description="MIDI channel (0-15)")


class PedalRequest(BaseModel):
    """Request to control a pedal."""
    on: bool = Field(..., description="Pedal state (true = pressed)")
    channel: Optional[int] = Field(None, ge=0, le=15, description="MIDI channel (0-15)")


class VelocityScaleRequest(BaseModel):
    """Request to set velocity scale."""
    percent: int = Field(..., ge=0, le=200, description="Velocity scale percentage (0-200)")


def ensure_connected(midi: MIDIController) -> None:
    """Ensure MIDI is connected, raise error if not."""
    if not midi.connected:
        if not midi.connect():
            raise HTTPException(status_code=503, detail="MIDI device not connected")


@router.post("/note/on")
async def note_on(request: NoteRequest, midi: MIDIController = Depends(get_midi_controller)):
    """Send a Note On message."""
    ensure_connected(midi)

    success = midi.note_on(request.note, request.velocity, request.channel)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send MIDI message")

    return {"success": True, "note": request.note, "velocity": request.velocity}


@router.post("/note/off")
async def note_off(request: NoteOffRequest, midi: MIDIController = Depends(get_midi_controller)):
    """Send a Note Off message."""
    ensure_connected(midi)

    success = midi.note_off(request.note, request.channel)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send MIDI message")

    return {"success": True, "note": request.note}


@router.post("/note")
async def send_note(request: NoteRequest, midi: MIDIController = Depends(get_midi_controller)):
    """
    Send a note (convenience endpoint).

    If velocity > 0, sends Note On. If velocity = 0, sends Note Off.
    """
    ensure_connected(midi)

    if request.velocity > 0:
        success = midi.note_on(request.note, request.velocity, request.channel)
    else:
        success = midi.note_off(request.note, request.channel)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send MIDI message")

    return {"success": True, "note": request.note, "velocity": request.velocity}


@router.post("/control")
async def control_change(
    request: ControlChangeRequest, midi: MIDIController = Depends(get_midi_controller)
):
    """Send a Control Change message."""
    ensure_connected(midi)

    success = midi.control_change(request.control, request.value, request.channel)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send MIDI message")

    return {"success": True, "control": request.control, "value": request.value}


@router.post("/sustain")
async def sustain_pedal(
    request: PedalRequest, midi: MIDIController = Depends(get_midi_controller)
):
    """Control the sustain pedal."""
    ensure_connected(midi)

    success = midi.sustain_pedal(request.on, request.channel)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send MIDI message")

    return {"success": True, "sustain": request.on}


@router.post("/soft")
async def soft_pedal(
    request: PedalRequest, midi: MIDIController = Depends(get_midi_controller)
):
    """Control the soft (una corda) pedal."""
    ensure_connected(midi)

    success = midi.soft_pedal(request.on, request.channel)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send MIDI message")

    return {"success": True, "soft": request.on}


@router.post("/panic")
async def panic(midi: MIDIController = Depends(get_midi_controller)):
    """
    Send All Notes Off (panic button).

    Immediately stops all playing notes on all channels.
    """
    ensure_connected(midi)

    success = midi.all_notes_off()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send panic message")

    return {"success": True, "message": "All notes off sent to all channels"}


@router.get("/velocity")
async def get_velocity_scale(midi: MIDIController = Depends(get_midi_controller)):
    """Get the current velocity scale percentage."""
    return {"velocity_scale": midi.velocity_scale}


@router.put("/velocity")
async def set_velocity_scale(
    request: VelocityScaleRequest, midi: MIDIController = Depends(get_midi_controller)
):
    """
    Set the velocity scale percentage.

    This scales all note velocities by the given percentage.
    100% = normal, 50% = half velocity (softer), 150% = 1.5x velocity (louder).
    """
    midi.velocity_scale = request.percent
    return {"success": True, "velocity_scale": midi.velocity_scale}
