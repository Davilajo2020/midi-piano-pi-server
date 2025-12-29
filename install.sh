#!/bin/bash
# MIDI Piano Pi Server Installation Script
# Sets up the Raspberry Pi as a network MIDI controller

set -e

echo "==================================="
echo "  MIDI Piano Pi Server Installation"
echo "==================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please run without sudo. The script will prompt for sudo when needed."
    exit 1
fi

INSTALL_DIR="$HOME/midi_piano_pi"
VENV_DIR="$INSTALL_DIR/venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Clone or update repository if needed
if [ ! -f "$INSTALL_DIR/pyproject.toml" ]; then
    echo "[0/7] Cloning repository..."
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
    fi
    git clone https://github.com/DavidWatkins/midi-piano-pi-server.git "$INSTALL_DIR"
elif [ "$SCRIPT_DIR" != "$INSTALL_DIR" ] && [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    echo "[0/7] Copying from source directory..."
    mkdir -p "$INSTALL_DIR"
    cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
fi

# 1. Install system dependencies
echo "[1/7] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-venv \
    python3-pip \
    libasound2-dev \
    libavahi-client-dev \
    libfmt-dev \
    cmake \
    git \
    fluidsynth

# 2. Create directories
echo "[2/7] Creating directories..."
sudo mkdir -p /var/lib/midi-piano-pi/uploads
sudo mkdir -p /var/lib/midi-piano-pi/catalog
sudo chown -R $USER:$USER /var/lib/midi-piano-pi
mkdir -p ~/.config/midi-piano-pi

# 3. Set up Python virtual environment
echo "[3/7] Setting up Python environment..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .

# 4. Build and install rtpmidid (Network MIDI)
echo "[4/7] Building rtpmidid for Network MIDI..."
if ! command -v rtpmidid &> /dev/null; then
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    git clone https://github.com/davidmoreno/rtpmidid.git
    cd rtpmidid
    mkdir build && cd build
    cmake ..
    make -j$(nproc)
    sudo cp src/rtpmidid /usr/local/bin/
    sudo cp lib/librtpmidid.so /usr/local/lib/
    sudo ldconfig
    cd "$INSTALL_DIR"
    rm -rf "$TEMP_DIR"
    echo "rtpmidid installed successfully"
else
    echo "rtpmidid already installed"
fi

# 5. Set up PipeWire RAOP for AirPlay broadcast
echo "[5/7] Configuring AirPlay broadcast..."
mkdir -p ~/.config/pipewire/pipewire.conf.d
cp config/pipewire.conf.d/raop-sink.conf ~/.config/pipewire/pipewire.conf.d/
systemctl --user restart pipewire || true

# 6. Install systemd services
echo "[6/7] Installing systemd services..."

# rtpmidid (system service)
sudo cp systemd/rtpmidid.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rtpmidid
sudo systemctl start rtpmidid || true

# Web interface (system service)
sudo cp systemd/midi-piano-pi-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable midi-piano-pi-web
sudo systemctl start midi-piano-pi-web || true

# FluidSynth broadcast (user service)
mkdir -p ~/.config/systemd/user
cp systemd/fluidsynth-broadcast.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable fluidsynth-broadcast

# 7. Check soundfont
echo "[7/7] Checking soundfont..."
if [ ! -f "$HOME/soundfonts/General Montage.sf2" ]; then
    echo ""
    echo "WARNING: Soundfont not found at ~/soundfonts/General Montage.sf2"
    echo "Please copy your SF2 soundfont to ~/soundfonts/ for FluidSynth."
    echo "You can use any GM-compatible soundfont."
    echo ""
fi

# Enable lingering for user services
loginctl enable-linger $USER 2>/dev/null || true

echo ""
echo "==================================="
echo "  Installation Complete!"
echo "==================================="
echo ""
echo "Services installed:"
echo "  - midi-piano-pi-web: Web interface on port 8080"
echo "  - rtpmidid: Network MIDI as 'MIDI Piano Pi'"
echo "  - fluidsynth-broadcast: AirPlay audio broadcast"
echo ""
echo "Access the web interface at: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "To start FluidSynth broadcast:"
echo "  systemctl --user start fluidsynth-broadcast"
echo ""
echo "For Network MIDI, connect from macOS Audio MIDI Setup."
echo ""
