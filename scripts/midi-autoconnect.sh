#!/bin/bash
# Auto-connect rtpmidid network MIDI sessions to DKC-800
# Runs periodically to catch new connections

DKC_PORT="24:0"  # USB Device 0x499:0x2003

# Find all rtpmidid client ports (except port 0 which is the server)
aconnect -l | grep -A1 "client 130:" | grep -E "^\s+[1-9]" | while read -r line; do
    port_num=$(echo "$line" | awk '{print $1}')
    # Connect if not already connected
    aconnect 130:$port_num $DKC_PORT 2>/dev/null && \
        echo "Connected 130:$port_num to $DKC_PORT"
done
