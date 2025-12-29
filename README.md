# Disklavier Pi

A Raspberry Pi service that turns a Yamaha Disklavier into a network-enabled smart piano. Provides a web interface, MIDI file playback, and WebSocket MIDI for integration with other applications.

## Features

- Web interface with virtual 88-key piano
- MIDI file catalog with search and playback queue
- WebSocket MIDI endpoint for external apps (e.g., Disklavier Karaoke)
- Network MIDI via rtpmidid (Apple MIDI compatible)
- AirPlay audio broadcast (piano to speakers)

> **Note on AirPlay:** AirPlay has inherent latency of ~2 seconds, making it unsuitable for real-time piano monitoring. It's best used for background music playback or when latency isn't critical. The feature is disabled by default and can be enabled in the Status tab of the web interface.

## Requirements

- Raspberry Pi 4 or 5
- Yamaha Disklavier with DKC-800 control unit
- USB cable connecting Pi to DKC-800
- Network connection

## Installation

### Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/DavidWatkins/disklavier-pi/main/install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/DavidWatkins/disklavier-pi.git
cd disklavier-pi
chmod +x install.sh
./install.sh
```

The installer will:
1. Install system dependencies (Python, ALSA, rtpmidid)
2. Create a Python virtual environment
3. Install the web service
4. Configure systemd to start on boot
5. Create necessary directories

### Post-Installation

Access the web interface at: `http://<pi-hostname>:8080`

Default hostname is usually `raspberrypi.local` or whatever you configured.

## Configuration

Edit `~/.config/disklavier/disklavier.yaml`:

```yaml
general:
  device_name: "Living Room Piano"
  log_level: "INFO"

web:
  host: "0.0.0.0"
  port: 8080

midi:
  device: "auto"
  channel: 0

catalog:
  directories:
    - "/var/lib/disklavier/catalog"
  scan_subdirs: true
  allowed_extensions: [".mid", ".midi", ".kar"]

uploads:
  directory: "/var/lib/disklavier/uploads"
  max_file_size_mb: 50
```

## Adding MIDI Files to Catalog

Copy MIDI/KAR files to the catalog directory:

```bash
# Single file
cp song.mid /var/lib/disklavier/catalog/

# Folder of files
cp -r ~/my-midi-collection /var/lib/disklavier/catalog/
```

Files are available immediately via the catalog API.

## Integration with Disklavier Karaoke

[Disklavier Karaoke](https://github.com/DavidWatkins/disklavier-karaoke) can connect to this service via WebSocket for reliable MIDI playback (bypasses Network MIDI latency issues).

In Disklavier Karaoke:
1. Go to Settings > Disklavier (MIDI)
2. Enter your Pi's hostname (e.g., `raspberrypi.local`)
3. Click Connect

All piano MIDI will route through the Pi to your Disklavier.

## API Reference

### Catalog Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/catalog` | List files (optional `path`, `search` params) |
| GET | `/api/v1/catalog/search?q=` | Search all catalogs |
| GET | `/api/v1/catalog/{file_id}` | Get file info |
| POST | `/api/v1/catalog/{file_id}/play` | Play a catalog file |

### Playback Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/playback` | Current playback state |
| POST | `/api/v1/playback/play` | Start/resume playback |
| POST | `/api/v1/playback/pause` | Pause playback |
| POST | `/api/v1/playback/stop` | Stop playback |
| PUT | `/api/v1/playback/tempo` | Set tempo (0.25-2.0) |

### Piano Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/piano/note` | Send a note |
| POST | `/api/v1/piano/panic` | All notes off |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/piano` | Real-time MIDI (JSON messages) |

WebSocket message format:
```json
{"type": "note_on", "note": 60, "velocity": 100}
{"type": "note_off", "note": 60}
{"type": "sustain", "on": true}
{"type": "panic"}
```

## Services

```bash
# Web interface
sudo systemctl status disklavier-web
sudo systemctl restart disklavier-web
sudo journalctl -u disklavier-web -f

# Network MIDI
sudo systemctl status rtpmidid
```

## Network MIDI (macOS)

1. Open Audio MIDI Setup > MIDI Studio (Cmd+2)
2. Double-click the Network icon
3. Find "Disklavier Pi" in Directory
4. Click Connect

Note: WebSocket connection via Disklavier Karaoke is more reliable than Network MIDI.

## Troubleshooting

**MIDI device not detected:**
```bash
aconnect -l   # List ALSA MIDI ports
amidi -l      # List raw MIDI devices
```

**Service won't start:**
```bash
sudo journalctl -u disklavier-web -n 50
```

**Check connectivity:**
```bash
curl http://localhost:8080/api/v1/status
```

## Development

```bash
cd disklavier-pi
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
uvicorn disklavier.api.app:app --reload --host 0.0.0.0 --port 8080
```

## License

MIT
