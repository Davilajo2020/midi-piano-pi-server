// WebSocket Manager for Disklavier Pi

class WebSocketManager {
    constructor(options = {}) {
        this.options = {
            url: options.url || `ws://${window.location.host}/ws/piano`,
            reconnectInterval: options.reconnectInterval || 3000,
            maxReconnectAttempts: options.maxReconnectAttempts || 10,
            onConnect: options.onConnect || (() => {}),
            onDisconnect: options.onDisconnect || (() => {}),
            onMessage: options.onMessage || (() => {}),
            onError: options.onError || (() => {}),
        };

        this.ws = null;
        this.reconnectAttempts = 0;
        this.isConnecting = false;
        this.pingInterval = null;
    }

    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            return;
        }

        this.isConnecting = true;
        console.log('WebSocket connecting to:', this.options.url);

        try {
            this.ws = new WebSocket(this.options.url);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                this.startPing();
                this.options.onConnect();
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.isConnecting = false;
                this.stopPing();
                this.options.onDisconnect();
                this.scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.options.onError(error);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.options.onMessage(data);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.isConnecting = false;
            this.scheduleReconnect();
        }
    }

    disconnect() {
        this.stopPing();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.options.reconnectInterval * Math.min(this.reconnectAttempts, 5);
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => this.connect(), delay);
    }

    startPing() {
        this.pingInterval = setInterval(() => {
            this.send({ type: 'ping' });
        }, 30000);
    }

    stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }

    // Convenience methods for piano control
    noteOn(note, velocity = 100, channel = null) {
        return this.send({
            type: 'note_on',
            note,
            velocity,
            channel,
        });
    }

    noteOff(note, channel = null) {
        return this.send({
            type: 'note_off',
            note,
            channel,
        });
    }

    controlChange(control, value, channel = null) {
        return this.send({
            type: 'control_change',
            control,
            value,
            channel,
        });
    }

    sustain(on) {
        return this.send({
            type: 'sustain',
            on,
        });
    }

    panic() {
        return this.send({
            type: 'panic',
        });
    }

    get isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Export for use in other modules
window.WebSocketManager = WebSocketManager;
