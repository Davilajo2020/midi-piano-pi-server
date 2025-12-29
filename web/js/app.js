// Disklavier Pi - Main Application

const App = {
    piano: null,
    ws: null,
    statusInterval: null,

    init() {
        console.log('Disklavier Pi initializing...');

        // Initialize WebSocket
        this.ws = new WebSocketManager({
            onConnect: () => this.onWebSocketConnect(),
            onDisconnect: () => this.onWebSocketDisconnect(),
            onMessage: (data) => this.onWebSocketMessage(data),
            onError: (error) => console.error('WebSocket error:', error),
        });

        // Initialize Piano
        this.piano = new VirtualPiano('piano-container', {
            startNote: 21,  // A0
            endNote: 108,   // C8
            onNoteOn: (note, velocity) => this.sendNoteOn(note, velocity),
            onNoteOff: (note) => this.sendNoteOff(note),
            onSustainChange: (on) => this.sendSustain(on),
        });

        // Connect WebSocket
        this.ws.connect();

        // Setup UI event handlers
        this.setupEventHandlers();

        // Start status polling
        this.startStatusPolling();

        // Initial status check
        this.checkStatus();
    },

    setupEventHandlers() {
        // Panic button
        const panicBtn = document.getElementById('panic-btn');
        if (panicBtn) {
            panicBtn.addEventListener('click', () => this.panic());
        }

        // Sustain pedal toggle (click to toggle on/off)
        const sustainBtn = document.getElementById('sustain-btn');
        if (sustainBtn) {
            sustainBtn.addEventListener('click', () => {
                const newState = !this.piano.sustainPedal;
                this.piano.setSustainPedal(newState);
            });
        }

        // Connect/Disconnect button
        const connectBtn = document.getElementById('connect-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.toggleMIDIConnection());
        }

        // Velocity slider
        const velocitySlider = document.getElementById('velocity-slider');
        const velocityValue = document.getElementById('velocity-value');
        if (velocitySlider) {
            velocitySlider.addEventListener('input', (e) => {
                const percent = parseInt(e.target.value);
                if (velocityValue) velocityValue.textContent = `${percent}%`;
            });
            velocitySlider.addEventListener('change', (e) => {
                this.setVelocityScale(parseInt(e.target.value));
            });
            // Load initial value
            this.loadVelocityScale();
        }

        // AirPlay toggle
        const airplayToggle = document.getElementById('airplay-toggle');
        if (airplayToggle) {
            airplayToggle.addEventListener('change', (e) => {
                this.toggleAirPlay(e.target.checked);
            });
            // Load initial state
            this.loadAirPlayStatus();
        }

        // Audio delay slider
        const audioDelaySlider = document.getElementById('audio-delay-slider');
        const audioDelayValue = document.getElementById('audio-delay-value');
        if (audioDelaySlider) {
            audioDelaySlider.addEventListener('input', (e) => {
                const ms = parseInt(e.target.value);
                if (audioDelayValue) audioDelayValue.textContent = `${ms}ms`;
            });
            audioDelaySlider.addEventListener('change', (e) => {
                this.setAudioDelay(parseInt(e.target.value));
            });
            // Load initial value
            this.loadAudioDelay();
        }
    },

    async loadVelocityScale() {
        try {
            const response = await fetch('/api/v1/piano/velocity');
            const data = await response.json();
            const slider = document.getElementById('velocity-slider');
            const value = document.getElementById('velocity-value');
            if (slider) slider.value = data.velocity_scale;
            if (value) value.textContent = `${data.velocity_scale}%`;
        } catch (error) {
            console.error('Failed to load velocity scale:', error);
        }
    },

    async setVelocityScale(percent) {
        try {
            await fetch('/api/v1/piano/velocity', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ percent }),
            });
        } catch (error) {
            console.error('Failed to set velocity scale:', error);
        }
    },

    async loadAirPlayStatus() {
        try {
            const response = await fetch('/api/v1/status/airplay');
            const data = await response.json();
            this.updateAirPlayUI(data.enabled);
        } catch (error) {
            console.error('Failed to load AirPlay status:', error);
        }
    },

    async toggleAirPlay(enable) {
        const endpoint = enable ? '/api/v1/status/airplay/enable' : '/api/v1/status/airplay/disable';
        try {
            const response = await fetch(endpoint, { method: 'POST' });
            const data = await response.json();
            this.updateAirPlayUI(data.enabled);
        } catch (error) {
            console.error('Failed to toggle AirPlay:', error);
        }
    },

    updateAirPlayUI(enabled) {
        const toggle = document.getElementById('airplay-toggle');
        const status = document.getElementById('airplay-status');
        if (toggle) toggle.checked = enabled;
        if (status) {
            status.textContent = enabled ? 'On' : 'Off';
            status.className = enabled ? 'status-text active' : 'status-text';
        }
    },

    async loadAudioDelay() {
        try {
            const response = await fetch('/api/v1/status/airplay/delay');
            const data = await response.json();
            const slider = document.getElementById('audio-delay-slider');
            const value = document.getElementById('audio-delay-value');
            if (slider) slider.value = data.delay_ms;
            if (value) value.textContent = `${data.delay_ms}ms`;
        } catch (error) {
            console.error('Failed to load audio delay:', error);
        }
    },

    async setAudioDelay(delay_ms) {
        try {
            await fetch('/api/v1/status/airplay/delay', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ delay_ms }),
            });
        } catch (error) {
            console.error('Failed to set audio delay:', error);
        }
    },

    sendNoteOn(note, velocity) {
        if (this.ws.isConnected) {
            this.ws.noteOn(note, velocity);
        } else {
            // Fallback to REST API
            fetch('/api/v1/piano/note/on', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note, velocity }),
            });
        }
    },

    sendNoteOff(note) {
        if (this.ws.isConnected) {
            this.ws.noteOff(note);
        } else {
            // Fallback to REST API
            fetch('/api/v1/piano/note/off', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note }),
            });
        }
    },

    sendSustain(on) {
        // Update button state
        const btn = document.getElementById('sustain-btn');
        if (btn) btn.classList.toggle('active', on);

        if (this.ws.isConnected) {
            this.ws.sustain(on);
        } else {
            fetch('/api/v1/piano/sustain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ on }),
            });
        }
    },

    panic() {
        this.piano.panic();
        if (this.ws.isConnected) {
            this.ws.panic();
        } else {
            fetch('/api/v1/piano/panic', { method: 'POST' });
        }
    },

    onWebSocketConnect() {
        this.updateConnectionStatus('connected');
    },

    onWebSocketDisconnect() {
        this.updateConnectionStatus('disconnected');
    },

    onWebSocketMessage(data) {
        switch (data.type) {
            case 'connected':
                console.log('MIDI device:', data.midi_device);
                this.updateMIDIStatus(data.midi_connected, data.midi_device);
                break;

            case 'midi_input':
                // Show piano keys being played on the physical piano
                this.piano.showMIDIInput(data.note, data.velocity);
                break;

            case 'note_sent':
                // Confirmation of note sent
                break;

            case 'error':
                console.error('Server error:', data.message);
                break;

            case 'pong':
                // Keepalive response
                break;
        }
    },

    updateConnectionStatus(status) {
        const indicator = document.getElementById('ws-status');
        const text = document.getElementById('ws-status-text');

        if (indicator && text) {
            indicator.className = `status-indicator ${status}`;
            text.textContent = status === 'connected' ? 'Connected' : 'Disconnected';
        }
    },

    updateMIDIStatus(connected, deviceName) {
        const indicator = document.getElementById('midi-status');
        const text = document.getElementById('midi-status-text');

        if (indicator && text) {
            indicator.className = `status-indicator ${connected ? 'connected' : 'disconnected'}`;
            text.textContent = connected ? (deviceName || 'Connected') : 'Disconnected';
        }
    },

    async checkStatus() {
        try {
            const response = await fetch('/api/v1/status');
            const data = await response.json();

            this.updateMIDIStatus(data.midi.connected, data.midi.device_name);
            this.updateSystemStats(data.system);
        } catch (error) {
            console.error('Status check failed:', error);
        }
    },

    updateSystemStats(system) {
        const cpuEl = document.getElementById('cpu-usage');
        const memEl = document.getElementById('mem-usage');
        const tempEl = document.getElementById('temperature');

        if (cpuEl) cpuEl.textContent = `${system.cpu_percent.toFixed(1)}%`;
        if (memEl) memEl.textContent = `${system.memory_percent.toFixed(1)}%`;
        if (tempEl && system.temperature_c) {
            tempEl.textContent = `${system.temperature_c.toFixed(1)}°C`;
        }
    },

    startStatusPolling() {
        this.statusInterval = setInterval(() => this.checkStatus(), 5000);
    },

    async toggleMIDIConnection() {
        const btn = document.getElementById('connect-btn');
        try {
            const statusResp = await fetch('/api/v1/status/midi');
            const status = await statusResp.json();

            if (status.connected) {
                await fetch('/api/v1/status/midi/disconnect', { method: 'POST' });
                btn.textContent = 'Connect MIDI';
            } else {
                await fetch('/api/v1/status/midi/connect', { method: 'POST' });
                btn.textContent = 'Disconnect MIDI';
            }

            this.checkStatus();
        } catch (error) {
            console.error('Failed to toggle MIDI connection:', error);
        }
    },
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => App.init());
