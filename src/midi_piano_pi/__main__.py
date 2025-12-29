"""Entry point for MIDI Piano Pi."""

import argparse
import logging
import sys
import time

from .core.config import get_settings
from .core.midi_controller import MIDIController


def setup_logging(level: str) -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def cmd_list_devices(args: argparse.Namespace) -> int:
    """List available MIDI devices."""
    controller = MIDIController()
    inputs, outputs = controller.list_devices()

    print("\n=== MIDI Input Devices ===")
    if inputs:
        for dev in inputs:
            print(f"  [{dev.port_index}] {dev.name}")
    else:
        print("  (none found)")

    print("\n=== MIDI Output Devices ===")
    if outputs:
        for dev in outputs:
            print(f"  [{dev.port_index}] {dev.name}")
    else:
        print("  (none found)")

    return 0


def cmd_test_note(args: argparse.Namespace) -> int:
    """Send a test note to the MIDI interface."""
    settings = get_settings()
    controller = MIDIController(
        device=args.device or settings.midi.device,
        channel=args.channel,
    )

    if not controller.connect():
        print("Failed to connect to MIDI device", file=sys.stderr)
        return 1

    print(f"Connected to: {controller.device_name}")
    print(f"Sending note {args.note} with velocity {args.velocity}...")

    controller.note_on(args.note, args.velocity)
    time.sleep(args.duration)
    controller.note_off(args.note)

    print("Done!")
    controller.disconnect()
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the web server."""
    import uvicorn
    from .api.app import create_app

    settings = get_settings()
    app = create_app()

    uvicorn.run(
        app,
        host=args.host or settings.web.host,
        port=args.port or settings.web.port,
        log_level=settings.general.log_level.lower(),
    )
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="midi-piano-pi",
        description="MIDI Piano Pi - Network-enabled MIDI piano control",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List devices command
    list_parser = subparsers.add_parser("list", help="List MIDI devices")
    list_parser.set_defaults(func=cmd_list_devices)

    # Test note command
    test_parser = subparsers.add_parser("test", help="Send a test note")
    test_parser.add_argument(
        "-n", "--note",
        type=int,
        default=60,
        help="MIDI note number (default: 60 = Middle C)",
    )
    test_parser.add_argument(
        "-V", "--velocity",
        type=int,
        default=100,
        help="Note velocity (default: 100)",
    )
    test_parser.add_argument(
        "-d", "--duration",
        type=float,
        default=0.5,
        help="Note duration in seconds (default: 0.5)",
    )
    test_parser.add_argument(
        "-c", "--channel",
        type=int,
        default=0,
        help="MIDI channel (default: 0)",
    )
    test_parser.add_argument(
        "--device",
        type=str,
        help="MIDI device name or 'auto'",
    )
    test_parser.set_defaults(func=cmd_test_note)

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the web server")
    serve_parser.add_argument(
        "-H", "--host",
        type=str,
        help="Host to bind to",
    )
    serve_parser.add_argument(
        "-p", "--port",
        type=int,
        help="Port to listen on",
    )
    serve_parser.set_defaults(func=cmd_serve)

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else get_settings().general.log_level
    setup_logging(log_level)

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
