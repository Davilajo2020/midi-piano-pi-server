"""MIDI Controller for Disklavier DKC-800 communication."""

import asyncio
import logging
import threading
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Optional

import rtmidi
from rtmidi.midiconstants import NOTE_ON, NOTE_OFF, CONTROL_CHANGE, PROGRAM_CHANGE

logger = logging.getLogger(__name__)


class MIDIStatus(IntEnum):
    """MIDI status bytes."""
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    POLY_AFTERTOUCH = 0xA0
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    CHANNEL_AFTERTOUCH = 0xD0
    PITCH_BEND = 0xE0


class ControlChange(IntEnum):
    """Common MIDI Control Change numbers."""
    SUSTAIN_PEDAL = 64
    SOSTENUTO_PEDAL = 66
    SOFT_PEDAL = 67
    ALL_SOUND_OFF = 120
    ALL_NOTES_OFF = 123


@dataclass
class MIDIDevice:
    """Information about a MIDI device."""
    name: str
    port_index: int
    is_virtual: bool = False


class MIDIController:
    """
    Controller for sending and receiving MIDI messages to/from the Disklavier.

    Handles USB MIDI communication with the DKC-800 unit.
    """

    def __init__(
        self,
        device: str = "auto",
        channel: int = 0,
        on_midi_input: Optional[Callable[[list[int], float], None]] = None,
    ):
        """
        Initialize the MIDI controller.

        Args:
            device: Device name or "auto" for auto-detection
            channel: Default MIDI channel (0-15)
            on_midi_input: Callback for incoming MIDI messages
        """
        self._device_pattern = device
        self._channel = channel
        self._on_midi_input = on_midi_input

        self._midi_out: Optional[rtmidi.MidiOut] = None
        self._midi_in: Optional[rtmidi.MidiIn] = None
        self._connected = False
        self._device_name: Optional[str] = None
        self._lock = threading.Lock()

        # Velocity scaling (0-200%, default 100%)
        self._velocity_scale = 100

    @property
    def connected(self) -> bool:
        """Check if MIDI device is connected."""
        return self._connected

    @property
    def device_name(self) -> Optional[str]:
        """Get the connected device name."""
        return self._device_name

    @property
    def velocity_scale(self) -> int:
        """Get the velocity scale percentage (0-200)."""
        return self._velocity_scale

    @velocity_scale.setter
    def velocity_scale(self, value: int) -> None:
        """Set the velocity scale percentage (0-200)."""
        self._velocity_scale = max(0, min(200, value))

    def _scale_velocity(self, velocity: int) -> int:
        """Apply velocity scaling to a velocity value."""
        scaled = int(velocity * self._velocity_scale / 100)
        return max(1, min(127, scaled))  # Clamp to valid MIDI range (1-127)

    def list_devices(self) -> tuple[list[MIDIDevice], list[MIDIDevice]]:
        """
        List available MIDI input and output devices.

        Returns:
            Tuple of (input_devices, output_devices)
        """
        midi_out = rtmidi.MidiOut()
        midi_in = rtmidi.MidiIn()

        output_devices = [
            MIDIDevice(name=name, port_index=i)
            for i, name in enumerate(midi_out.get_ports())
        ]

        input_devices = [
            MIDIDevice(name=name, port_index=i)
            for i, name in enumerate(midi_in.get_ports())
        ]

        del midi_out, midi_in
        return input_devices, output_devices

    def _find_device(self, ports: list[str], pattern: str) -> Optional[int]:
        """Find a device matching the pattern."""
        if pattern == "auto":
            # Look for Yamaha/DKC devices first
            for i, name in enumerate(ports):
                name_lower = name.lower()
                if "yamaha" in name_lower or "dkc" in name_lower or "0499" in name_lower:
                    return i

            # Fall back to first non-through device
            for i, name in enumerate(ports):
                if "through" not in name.lower():
                    return i

            return None

        # Look for exact or partial match
        for i, name in enumerate(ports):
            if pattern in name or name == pattern:
                return i

        return None

    def connect(self) -> bool:
        """
        Connect to the MIDI device.

        Returns:
            True if connection successful
        """
        with self._lock:
            if self._connected:
                return True

            try:
                # Initialize MIDI output
                self._midi_out = rtmidi.MidiOut()
                out_ports = self._midi_out.get_ports()

                out_port = self._find_device(out_ports, self._device_pattern)
                if out_port is None:
                    logger.error("No MIDI output device found matching: %s", self._device_pattern)
                    return False

                self._midi_out.open_port(out_port)
                self._device_name = out_ports[out_port]
                logger.info("Opened MIDI output: %s", self._device_name)

                # Initialize MIDI input
                self._midi_in = rtmidi.MidiIn()
                in_ports = self._midi_in.get_ports()

                in_port = self._find_device(in_ports, self._device_pattern)
                if in_port is not None:
                    self._midi_in.open_port(in_port)
                    self._midi_in.set_callback(self._handle_midi_input)
                    logger.info("Opened MIDI input: %s", in_ports[in_port])

                self._connected = True
                return True

            except Exception as e:
                logger.exception("Failed to connect to MIDI device: %s", e)
                self._cleanup()
                return False

    def disconnect(self) -> None:
        """Disconnect from the MIDI device."""
        with self._lock:
            self._cleanup()

    def _cleanup(self) -> None:
        """Clean up MIDI resources."""
        if self._midi_in:
            self._midi_in.cancel_callback()
            self._midi_in.close_port()
            del self._midi_in
            self._midi_in = None

        if self._midi_out:
            self._midi_out.close_port()
            del self._midi_out
            self._midi_out = None

        self._connected = False
        self._device_name = None

    def _handle_midi_input(self, event: tuple[list[int], float], data: None = None) -> None:
        """Handle incoming MIDI messages."""
        message, delta_time = event
        if self._on_midi_input:
            self._on_midi_input(message, delta_time)

    def _send(self, message: list[int]) -> bool:
        """Send a raw MIDI message."""
        if not self._connected or not self._midi_out:
            logger.warning("Cannot send MIDI: not connected")
            return False

        try:
            self._midi_out.send_message(message)
            return True
        except Exception as e:
            logger.exception("Failed to send MIDI message: %s", e)
            return False

    def note_on(self, note: int, velocity: int = 100, channel: Optional[int] = None) -> bool:
        """
        Send a Note On message.

        Args:
            note: MIDI note number (0-127), 60 = Middle C
            velocity: Note velocity (1-127), 0 sends Note Off
            channel: MIDI channel (0-15), None uses default
        """
        if velocity == 0:
            return self.note_off(note, channel)

        ch = channel if channel is not None else self._channel
        scaled_velocity = self._scale_velocity(velocity)
        message = [MIDIStatus.NOTE_ON | (ch & 0x0F), note & 0x7F, scaled_velocity & 0x7F]
        return self._send(message)

    def note_off(self, note: int, channel: Optional[int] = None) -> bool:
        """
        Send a Note Off message.

        Args:
            note: MIDI note number (0-127)
            channel: MIDI channel (0-15), None uses default
        """
        ch = channel if channel is not None else self._channel
        message = [MIDIStatus.NOTE_OFF | (ch & 0x0F), note & 0x7F, 0]
        return self._send(message)

    def control_change(
        self, control: int, value: int, channel: Optional[int] = None
    ) -> bool:
        """
        Send a Control Change message.

        Args:
            control: Controller number (0-127)
            value: Controller value (0-127)
            channel: MIDI channel (0-15), None uses default
        """
        ch = channel if channel is not None else self._channel
        message = [MIDIStatus.CONTROL_CHANGE | (ch & 0x0F), control & 0x7F, value & 0x7F]
        return self._send(message)

    def sustain_pedal(self, on: bool, channel: Optional[int] = None) -> bool:
        """Control the sustain pedal."""
        return self.control_change(ControlChange.SUSTAIN_PEDAL, 127 if on else 0, channel)

    def soft_pedal(self, on: bool, channel: Optional[int] = None) -> bool:
        """Control the soft pedal."""
        return self.control_change(ControlChange.SOFT_PEDAL, 127 if on else 0, channel)

    def all_notes_off(self, channel: Optional[int] = None) -> bool:
        """
        Send All Notes Off message (panic).

        Args:
            channel: MIDI channel, None sends to all channels
        """
        if channel is not None:
            return self.control_change(ControlChange.ALL_NOTES_OFF, 0, channel)

        # Send to all channels
        success = True
        for ch in range(16):
            if not self.control_change(ControlChange.ALL_NOTES_OFF, 0, ch):
                success = False
        return success

    def pitch_bend(self, value: int, channel: Optional[int] = None) -> bool:
        """
        Send a Pitch Bend message.

        Args:
            value: Pitch bend value (0-16383), 8192 = center
            channel: MIDI channel (0-15), None uses default
        """
        ch = channel if channel is not None else self._channel
        lsb = value & 0x7F
        msb = (value >> 7) & 0x7F
        message = [MIDIStatus.PITCH_BEND | (ch & 0x0F), lsb, msb]
        return self._send(message)

    def program_change(self, program: int, channel: Optional[int] = None) -> bool:
        """
        Send a Program Change message.

        Args:
            program: Program number (0-127)
            channel: MIDI channel (0-15), None uses default
        """
        ch = channel if channel is not None else self._channel
        message = [MIDIStatus.PROGRAM_CHANGE | (ch & 0x0F), program & 0x7F]
        return self._send(message)


# Global singleton instance
_controller: Optional[MIDIController] = None


def get_midi_controller() -> MIDIController:
    """Get the global MIDI controller instance."""
    global _controller
    if _controller is None:
        from .config import get_settings
        settings = get_settings()
        _controller = MIDIController(
            device=settings.midi.device,
            channel=settings.midi.channel,
        )
    return _controller
