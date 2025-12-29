// Virtual Piano Keyboard Component

class VirtualPiano {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            startNote: options.startNote || 21,  // A0
            endNote: options.endNote || 108,     // C8
            onNoteOn: options.onNoteOn || (() => {}),
            onNoteOff: options.onNoteOff || (() => {}),
            onSustainChange: options.onSustainChange || (() => {}),
        };

        this.activeNotes = new Set();
        this.sustainPedal = false;
        this.sustainedNotes = new Set();

        this.init();
    }

    init() {
        this.container.innerHTML = '';
        this.container.className = 'piano-container';

        // Create keyboard wrapper
        const keyboard = document.createElement('div');
        keyboard.className = 'piano-keyboard';

        // Generate keys
        for (let note = this.options.startNote; note <= this.options.endNote; note++) {
            const key = this.createKey(note);
            keyboard.appendChild(key);
        }

        this.container.appendChild(keyboard);

        // Add keyboard event listeners
        this.setupKeyboardInput();
    }

    createKey(note) {
        const isBlack = this.isBlackKey(note);
        const key = document.createElement('div');
        key.className = `piano-key ${isBlack ? 'black-key' : 'white-key'}`;
        key.dataset.note = note;
        key.dataset.noteName = this.getNoteName(note);

        // Add note label for white keys
        if (!isBlack && (note % 12 === 0 || note === this.options.startNote)) {
            const label = document.createElement('span');
            label.className = 'key-label';
            label.textContent = this.getNoteName(note);
            key.appendChild(label);
        }

        // Mouse/touch events
        key.addEventListener('mousedown', (e) => this.handleNoteOn(note, e));
        key.addEventListener('mouseup', () => this.handleNoteOff(note));
        key.addEventListener('mouseleave', () => {
            if (this.activeNotes.has(note)) {
                this.handleNoteOff(note);
            }
        });
        key.addEventListener('mouseenter', (e) => {
            if (e.buttons === 1) {
                this.handleNoteOn(note, e);
            }
        });

        // Touch events
        key.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.handleNoteOn(note, e);
        });
        key.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.handleNoteOff(note);
        });

        return key;
    }

    isBlackKey(note) {
        const noteInOctave = note % 12;
        return [1, 3, 6, 8, 10].includes(noteInOctave);
    }

    getNoteName(note) {
        const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        const octave = Math.floor(note / 12) - 1;
        const noteName = noteNames[note % 12];
        return `${noteName}${octave}`;
    }

    handleNoteOn(note, event) {
        if (this.activeNotes.has(note)) return;

        this.activeNotes.add(note);

        // Calculate velocity from click position (center = max velocity)
        let velocity = 100;
        if (event && event.target) {
            const rect = event.target.getBoundingClientRect();
            const y = event.clientY || (event.touches && event.touches[0].clientY);
            if (y) {
                const relY = (y - rect.top) / rect.height;
                velocity = Math.floor(40 + relY * 87);  // 40-127 range
            }
        }

        this.highlightKey(note, true);
        this.options.onNoteOn(note, velocity);
    }

    handleNoteOff(note) {
        if (!this.activeNotes.has(note)) return;

        this.activeNotes.delete(note);

        if (this.sustainPedal) {
            this.sustainedNotes.add(note);
        } else {
            this.highlightKey(note, false);
            this.options.onNoteOff(note);
        }
    }

    highlightKey(note, active) {
        const key = this.container.querySelector(`[data-note="${note}"]`);
        if (key) {
            if (active) {
                key.classList.add('active');
            } else {
                key.classList.remove('active');
            }
        }
    }

    setSustainPedal(on) {
        this.sustainPedal = on;
        this.options.onSustainChange(on);

        if (!on) {
            // Release all sustained notes
            for (const note of this.sustainedNotes) {
                if (!this.activeNotes.has(note)) {
                    this.highlightKey(note, false);
                    this.options.onNoteOff(note);
                }
            }
            this.sustainedNotes.clear();
        }
    }

    setupKeyboardInput() {
        // Map computer keys to piano notes (starting at middle C)
        const keyMap = {
            // Lower row - C4 to B4
            'a': 60, 'w': 61, 's': 62, 'e': 63, 'd': 64, 'f': 65,
            't': 66, 'g': 67, 'y': 68, 'h': 69, 'u': 70, 'j': 71,
            // Upper row - C5 to E5
            'k': 72, 'o': 73, 'l': 74, 'p': 75, ';': 76, "'": 77,
            // Lower octave
            'z': 48, 'x': 50, 'c': 52, 'v': 53, 'b': 55, 'n': 57, 'm': 59,
        };

        const pressedKeys = new Set();

        document.addEventListener('keydown', (e) => {
            if (e.repeat) return;

            const key = e.key.toLowerCase();

            // Space bar toggles sustain pedal
            if (e.code === 'Space') {
                e.preventDefault();
                this.setSustainPedal(!this.sustainPedal);
                return;
            }

            if (keyMap[key] && !pressedKeys.has(key)) {
                e.preventDefault();
                pressedKeys.add(key);
                const note = keyMap[key];
                this.handleNoteOn(note, null);
            }
        });

        document.addEventListener('keyup', (e) => {
            const key = e.key.toLowerCase();

            // Space is now toggle, no action on keyup
            if (e.code === 'Space') {
                e.preventDefault();
                return;
            }

            if (keyMap[key]) {
                pressedKeys.delete(key);
                const note = keyMap[key];
                this.handleNoteOff(note);
            }
        });
    }

    // External highlight (for showing MIDI input from piano)
    showMIDIInput(note, velocity) {
        const key = this.container.querySelector(`[data-note="${note}"]`);
        if (key) {
            if (velocity > 0) {
                key.classList.add('midi-input');
            } else {
                key.classList.remove('midi-input');
            }
        }
    }

    panic() {
        // Release all notes
        for (const note of this.activeNotes) {
            this.highlightKey(note, false);
        }
        for (const note of this.sustainedNotes) {
            this.highlightKey(note, false);
        }
        this.activeNotes.clear();
        this.sustainedNotes.clear();
        this.sustainPedal = false;
    }
}

// Export for use in other modules
window.VirtualPiano = VirtualPiano;
