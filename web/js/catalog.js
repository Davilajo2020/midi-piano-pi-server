// Catalog and Queue Management

const Catalog = {
    currentPath: '',
    queue: [],
    allFiles: [],

    async init() {
        this.setupEventListeners();
        await this.loadCatalog();
    },

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });

        // Search
        const searchBtn = document.getElementById('search-btn');
        const searchInput = document.getElementById('catalog-search');

        searchBtn.addEventListener('click', () => this.search(searchInput.value));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.search(searchInput.value);
        });

        // Queue controls
        document.getElementById('shuffle-btn').addEventListener('click', () => this.shuffleQueue());
        document.getElementById('clear-queue-btn').addEventListener('click', () => this.clearQueue());

        // Skip button
        const skipBtn = document.getElementById('skip-btn');
        if (skipBtn) {
            skipBtn.addEventListener('click', () => this.playNext());
        }
    },

    switchTab(tabId) {
        // Update buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === tabId + '-tab');
        });
    },

    async loadCatalog(path = '') {
        this.currentPath = path;

        try {
            const url = path
                ? `/api/v1/catalog?path=${encodeURIComponent(path)}`
                : '/api/v1/catalog';

            const response = await fetch(url);
            const data = await response.json();

            this.renderCatalog(data);
            this.updateBreadcrumb(path);
            this.updateCount(data.total_files, data.directories.length);
        } catch (error) {
            console.error('Failed to load catalog:', error);
        }
    },

    async search(query) {
        if (!query.trim()) {
            this.loadCatalog(this.currentPath);
            return;
        }

        try {
            const response = await fetch(`/api/v1/catalog/search?q=${encodeURIComponent(query)}&limit=100`);
            const data = await response.json();

            this.renderSearchResults(data.results);
            this.updateCount(data.total, 0);
        } catch (error) {
            console.error('Search failed:', error);
        }
    },

    renderCatalog(data) {
        const dirsContainer = document.getElementById('catalog-dirs');
        const filesContainer = document.getElementById('catalog-files');

        // Render directories
        if (data.directories.length > 0) {
            dirsContainer.innerHTML = data.directories.map(dir => `
                <div class="catalog-dir" data-path="${dir.path}">
                    <span class="dir-icon">folder</span>
                    <span class="dir-name">${dir.name}</span>
                    <span class="dir-count">${dir.file_count} files</span>
                </div>
            `).join('');

            dirsContainer.querySelectorAll('.catalog-dir').forEach(el => {
                el.addEventListener('click', () => this.loadCatalog(el.dataset.path));
            });
        } else {
            dirsContainer.innerHTML = '';
        }

        // Render files
        if (data.files.length > 0) {
            filesContainer.innerHTML = data.files.map(file => `
                <div class="catalog-file" data-id="${file.id}">
                    <div class="file-info">
                        <span class="file-name">${file.name}</span>
                        <span class="file-meta">${file.extension} - ${this.formatSize(file.size)}</span>
                    </div>
                    <div class="file-actions">
                        <button class="play-btn" data-id="${file.id}">Play</button>
                        <button class="queue-btn" data-id="${file.id}" data-name="${file.name}">Add</button>
                    </div>
                </div>
            `).join('');

            filesContainer.querySelectorAll('.play-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.playFile(btn.dataset.id);
                });
            });

            filesContainer.querySelectorAll('.queue-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.addToQueue(btn.dataset.id, btn.dataset.name);
                });
            });
        } else if (data.directories.length === 0) {
            filesContainer.innerHTML = '<p class="empty-message">No files in this directory</p>';
        } else {
            filesContainer.innerHTML = '';
        }
    },

    renderSearchResults(results) {
        const dirsContainer = document.getElementById('catalog-dirs');
        const filesContainer = document.getElementById('catalog-files');

        dirsContainer.innerHTML = '';

        if (results.length > 0) {
            filesContainer.innerHTML = results.map(file => `
                <div class="catalog-file" data-id="${file.id}">
                    <div class="file-info">
                        <span class="file-name">${file.name}</span>
                        <span class="file-meta">${file.directory || 'Root'} - ${file.extension}</span>
                    </div>
                    <div class="file-actions">
                        <button class="play-btn" data-id="${file.id}">Play</button>
                        <button class="queue-btn" data-id="${file.id}" data-name="${file.name}">Add</button>
                    </div>
                </div>
            `).join('');

            filesContainer.querySelectorAll('.play-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.playFile(btn.dataset.id);
                });
            });

            filesContainer.querySelectorAll('.queue-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.addToQueue(btn.dataset.id, btn.dataset.name);
                });
            });
        } else {
            filesContainer.innerHTML = '<p class="empty-message">No results found</p>';
        }
    },

    updateBreadcrumb(path) {
        const container = document.getElementById('breadcrumb');
        const parts = path ? path.split('/') : [];

        let html = '<span class="crumb" data-path="">Home</span>';
        let currentPath = '';

        parts.forEach((part, i) => {
            currentPath += (i > 0 ? '/' : '') + part;
            html += ` <span class="separator">/</span> <span class="crumb" data-path="${currentPath}">${part}</span>`;
        });

        container.innerHTML = html;

        container.querySelectorAll('.crumb').forEach(el => {
            el.addEventListener('click', () => this.loadCatalog(el.dataset.path));
        });
    },

    updateCount(files, dirs) {
        const el = document.getElementById('catalog-count');
        if (dirs > 0) {
            el.textContent = `${dirs} folders, ${files} files`;
        } else {
            el.textContent = `${files} files`;
        }
    },

    async playFile(fileId) {
        try {
            const response = await fetch(`/api/v1/catalog/${encodeURIComponent(fileId)}/play`, {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                // Update player UI
                document.getElementById('now-playing').textContent = data.file;
                this.switchTab('piano');
            }
        } catch (error) {
            console.error('Failed to play file:', error);
        }
    },

    addToQueue(fileId, fileName) {
        // Avoid duplicates
        if (this.queue.find(item => item.id === fileId)) {
            return;
        }

        this.queue.push({ id: fileId, name: fileName });
        this.renderQueue();

        // If nothing is playing and this is the first item, start playing
        if (this.queue.length === 1) {
            this.playNext();
        }
    },

    removeFromQueue(index) {
        this.queue.splice(index, 1);
        this.renderQueue();
    },

    shuffleQueue() {
        // Fisher-Yates shuffle
        for (let i = this.queue.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.queue[i], this.queue[j]] = [this.queue[j], this.queue[i]];
        }
        this.renderQueue();
    },

    clearQueue() {
        this.queue = [];
        this.renderQueue();
    },

    async playNext() {
        if (this.queue.length === 0) return;

        const next = this.queue.shift();
        this.renderQueue();
        await this.playFile(next.id);
    },

    renderQueue() {
        const container = document.getElementById('queue-list');

        if (this.queue.length === 0) {
            container.innerHTML = '<p class="empty-message">Queue is empty. Add songs from the catalog below.</p>';
            return;
        }

        container.innerHTML = this.queue.map((item, index) => `
            <div class="queue-item">
                <span class="queue-number">${index + 1}</span>
                <span class="queue-name">${item.name}</span>
                <button class="remove-btn" data-index="${index}">Remove</button>
            </div>
        `).join('');

        container.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', () => this.removeFromQueue(parseInt(btn.dataset.index)));
        });
    },

    formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Catalog.init();
});
