// MIDI File Player Controls

class MIDIPlayerUI {
    constructor() {
        this.currentFile = null;
        this.isPlaying = false;
        this.statusInterval = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadFileList();
        // Load initial playback status to sync UI state
        this.updatePlaybackStatus();
    }

    setupEventListeners() {
        // File upload
        const uploadInput = document.getElementById('file-upload');
        const uploadBtn = document.getElementById('upload-btn');
        const uploadArea = document.getElementById('upload-area');

        if (uploadInput) {
            uploadInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => uploadInput?.click());
        }

        // Drag and drop
        if (uploadArea) {
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('drag-over');
            });
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('drag-over');
            });
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.uploadFile(files[0]);
                }
            });
        }

        // Playback controls
        document.getElementById('play-btn')?.addEventListener('click', () => this.play());
        document.getElementById('pause-btn')?.addEventListener('click', () => this.pause());
        document.getElementById('stop-btn')?.addEventListener('click', () => this.stop());
        document.getElementById('skip-btn')?.addEventListener('click', () => this.skip());

        // Seek bar
        const seekBar = document.getElementById('seek-bar');
        if (seekBar) {
            seekBar.addEventListener('input', (e) => this.seek(parseInt(e.target.value)));
        }

        // Tempo control
        const tempoSlider = document.getElementById('tempo-slider');
        const tempoValue = document.getElementById('tempo-value');
        if (tempoSlider) {
            tempoSlider.addEventListener('input', (e) => {
                const percent = parseInt(e.target.value);
                if (tempoValue) tempoValue.textContent = `${percent}%`;
            });
            tempoSlider.addEventListener('change', (e) => {
                this.setTempo(parseInt(e.target.value));
            });
        }

        // Channel mode toggle
        const channelToggle = document.getElementById('play-all-channels');
        if (channelToggle) {
            channelToggle.addEventListener('change', (e) => {
                this.setChannelMode(e.target.checked);
            });
        }
    }

    async handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            await this.uploadFile(file);
        }
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/v1/files/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const fileInfo = await response.json();
            console.log('Uploaded:', fileInfo);

            // Refresh file list
            await this.loadFileList();

            // Auto-load the uploaded file
            await this.loadFile(fileInfo.id);

        } catch (error) {
            console.error('Upload error:', error);
            alert('Upload failed: ' + error.message);
        }
    }

    async loadFileList() {
        try {
            const response = await fetch('/api/v1/files');
            const data = await response.json();

            this.renderFileList(data.files);
        } catch (error) {
            console.error('Failed to load file list:', error);
        }
    }

    renderFileList(files) {
        const container = document.getElementById('file-list');
        if (!container) return;

        if (files.length === 0) {
            container.innerHTML = '<p class="no-files">No files uploaded yet</p>';
            return;
        }

        container.innerHTML = files.map(file => `
            <div class="file-item" data-id="${file.id}">
                <div class="file-info">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${this.formatSize(file.size)}</span>
                </div>
                <div class="file-actions">
                    <button class="file-btn load-btn" onclick="playerUI.loadFile('${file.id}')">Load</button>
                    <button class="file-btn delete-btn" onclick="playerUI.deleteFile('${file.id}')">Delete</button>
                </div>
            </div>
        `).join('');
    }

    async loadFile(fileId) {
        try {
            const response = await fetch('/api/v1/playback/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_id: fileId }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to load file');
            }

            const result = await response.json();
            this.currentFile = result.file;

            // Update UI
            this.updateNowPlaying(result.file);
            this.updatePlaybackStatus();

            // Highlight loaded file
            document.querySelectorAll('.file-item').forEach(el => {
                el.classList.toggle('active', el.dataset.id === fileId);
            });

        } catch (error) {
            console.error('Load error:', error);
            alert('Failed to load file: ' + error.message);
        }
    }

    async deleteFile(fileId) {
        if (!confirm('Delete this file?')) return;

        try {
            const response = await fetch(`/api/v1/files/${fileId}`, {
                method: 'DELETE',
            });

            if (response.ok) {
                await this.loadFileList();
            }
        } catch (error) {
            console.error('Delete error:', error);
        }
    }

    async play() {
        try {
            await fetch('/api/v1/playback/play', { method: 'POST' });
            this.isPlaying = true;
            this.startStatusPolling();
            this.updatePlaybackButtons();
        } catch (error) {
            console.error('Play error:', error);
        }
    }

    async pause() {
        try {
            await fetch('/api/v1/playback/pause', { method: 'POST' });
            this.isPlaying = false;
            this.updatePlaybackButtons();
        } catch (error) {
            console.error('Pause error:', error);
        }
    }

    async stop() {
        try {
            await fetch('/api/v1/playback/stop', { method: 'POST' });
            this.isPlaying = false;
            this.stopStatusPolling();
            this.updatePlaybackStatus();
            this.updatePlaybackButtons();
        } catch (error) {
            console.error('Stop error:', error);
        }
    }

    async skip() {
        try {
            const response = await fetch('/api/v1/playback/queue/next', { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.isPlaying = true;
                this.startStatusPolling();
                this.updatePlaybackButtons();
                if (result.playing) {
                    this.updateNowPlaying({ name: result.playing.name });
                }
                // Refresh queue display
                if (window.catalogUI) {
                    window.catalogUI.loadQueue();
                }
            } else {
                console.log('Skip: ' + (result.message || 'Queue empty'));
            }
        } catch (error) {
            console.error('Skip error:', error);
        }
    }

    async seek(positionMs) {
        try {
            await fetch('/api/v1/playback/seek', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ position_ms: positionMs }),
            });
        } catch (error) {
            console.error('Seek error:', error);
        }
    }

    async setTempo(percent) {
        try {
            await fetch('/api/v1/playback/tempo', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ percent }),
            });
        } catch (error) {
            console.error('Tempo error:', error);
        }
    }

    async setChannelMode(playAll) {
        try {
            const response = await fetch('/api/v1/playback/channels', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ play_all: playAll }),
            });
            const result = await response.json();
            this.updateChannelInfo(result.piano_channels, playAll);
        } catch (error) {
            console.error('Channel mode error:', error);
        }
    }

    updateChannelInfo(pianoChannels, playAll) {
        const channelInfo = document.getElementById('piano-channels');
        if (channelInfo && pianoChannels && pianoChannels.length > 0) {
            const mode = playAll ? 'All channels' : 'Piano only';
            channelInfo.textContent = `${mode} (piano: ch ${pianoChannels.join(', ')})`;
        }
    }

    startStatusPolling() {
        this.stopStatusPolling();
        this.statusInterval = setInterval(() => this.updatePlaybackStatus(), 500);
    }

    stopStatusPolling() {
        if (this.statusInterval) {
            clearInterval(this.statusInterval);
            this.statusInterval = null;
        }
    }

    async updatePlaybackStatus() {
        try {
            const response = await fetch('/api/v1/playback');
            const status = await response.json();

            // Update seek bar
            const seekBar = document.getElementById('seek-bar');
            if (seekBar) {
                seekBar.max = status.duration_ms;
                seekBar.value = status.position_ms;
            }

            // Update time display
            const currentTime = document.getElementById('current-time');
            const totalTime = document.getElementById('total-time');
            if (currentTime) currentTime.textContent = this.formatTime(status.position_ms);
            if (totalTime) totalTime.textContent = this.formatTime(status.duration_ms);

            // Update state
            this.isPlaying = status.state === 'playing';
            this.updatePlaybackButtons();

            // Update channel toggle state
            const channelToggle = document.getElementById('play-all-channels');
            if (channelToggle) {
                channelToggle.checked = status.play_all_channels;
            }
            this.updateChannelInfo(status.piano_channels, status.play_all_channels);

            // Stop polling if stopped
            if (status.state === 'stopped' && this.statusInterval) {
                this.stopStatusPolling();
            }

        } catch (error) {
            console.error('Status update error:', error);
        }
    }

    updateNowPlaying(file) {
        const nowPlaying = document.getElementById('now-playing');
        if (nowPlaying && file) {
            nowPlaying.textContent = file.name;
        }
    }

    updatePlaybackButtons() {
        const playBtn = document.getElementById('play-btn');
        const pauseBtn = document.getElementById('pause-btn');

        if (playBtn) playBtn.disabled = this.isPlaying;
        if (pauseBtn) pauseBtn.disabled = !this.isPlaying;
    }

    formatTime(ms) {
        const seconds = Math.floor(ms / 1000);
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
}

// Global instance
let playerUI;
document.addEventListener('DOMContentLoaded', () => {
    playerUI = new MIDIPlayerUI();
});
