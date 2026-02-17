// ClassMate Web App - Real-time Transcription
class ClassMateWebApp {
    constructor() {
        this.ws = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.sessionId = null;
        this.userId = null;
        this.chunkIndex = 0;
        this.transcript = [];
        this.speakers = new Set();
        
        this.initializeApp();
    }

    async initializeApp() {
        this.setupEventListeners();
        this.loadUserSession();
        this.setupServiceWorker();
    }

    setupEventListeners() {
        // Recording controls
        const recordBtn = document.getElementById('record-btn');
        const stopBtn = document.getElementById('stop-btn');
        const pauseBtn = document.getElementById('pause-btn');
        
        if (recordBtn) {
            recordBtn.addEventListener('click', () => this.startRecording());
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopRecording());
        }
        
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.pauseRecording());
        }

        // Navigation
        document.querySelectorAll('[data-page]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateTo(link.dataset.page);
            });
        });

        // Settings
        const languageSelect = document.getElementById('language-select');
        if (languageSelect) {
            languageSelect.addEventListener('change', (e) => {
                this.updateLanguage(e.target.value);
            });
        }
    }

    async loadUserSession() {
        // Load user session from localStorage or API
        const storedSession = localStorage.getItem('classmate_session');
        if (storedSession) {
            const session = JSON.parse(storedSession);
            this.userId = session.userId;
            this.sessionId = session.sessionId;
        } else {
            // Create new session
            await this.createNewSession();
        }
    }

    async createNewSession() {
        try {
            const response = await fetch('/api/v1/sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: this.generateUserId(),
                    title: `Meeting ${new Date().toLocaleString()}`
                })
            });

            if (response.ok) {
                const session = await response.json();
                this.sessionId = session.id;
                this.userId = session.user_id;
                
                // Save to localStorage
                localStorage.setItem('classmate_session', JSON.stringify({
                    userId: this.userId,
                    sessionId: this.sessionId
                }));
            }
        } catch (error) {
            console.error('Failed to create session:', error);
            this.showError('Failed to create session');
        }
    }

    generateUserId() {
        return 'user_' + Math.random().toString(36).substr(2, 9);
    }

    async setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/sw.js');
                console.log('ServiceWorker registration successful');
            } catch (error) {
                console.log('ServiceWorker registration failed');
            }
        }
    }

    async startRecording() {
        try {
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000
                } 
            });

            // Create WebSocket connection
            await this.connectWebSocket();

            // Setup MediaRecorder
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            this.audioChunks = [];
            this.chunkIndex = 0;
            this.isRecording = true;

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                    this.sendAudioChunk(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.processRecording();
            };

            // Start recording in 1-second chunks
            this.mediaRecorder.start(1000);
            
            this.updateUI('recording');
            this.showSuccess('Recording started');

        } catch (error) {
            console.error('Failed to start recording:', error);
            this.showError('Failed to access microphone');
        }
    }

    async connectWebSocket() {
        const wsUrl = `ws://localhost:8000/api/v1/ws/transcribe/${this.sessionId}/${this.userId}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.showConnectionStatus('Connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.showConnectionStatus('Disconnected');
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showError('Connection error');
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'connection_established':
                console.log('WebSocket connection established');
                break;
                
            case 'transcription_result':
                this.displayTranscription(data);
                break;
                
            case 'session_transcript':
                this.displayFullTranscript(data);
                break;
                
            case 'error':
                this.showError(data.error);
                break;
                
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    displayTranscription(data) {
        const transcriptContainer = document.getElementById('live-transcript');
        if (!transcriptContainer) return;

        // Add to transcript array
        this.transcript.push({
            text: data.text,
            timestamp: data.timestamp,
            speaker: data.speaker || 'Unknown',
            confidence: data.confidence
        });

        // Update speakers set
        if (data.speaker) {
            this.speakers.add(data.speaker);
        }

        // Display in UI
        const transcriptElement = document.createElement('div');
        transcriptElement.className = 'transcript-segment mb-4 p-3 bg-gray-50 rounded-lg';
        transcriptElement.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <span class="font-semibold text-sm text-blue-600">${data.speaker || 'Unknown'}</span>
                <span class="text-xs text-gray-500">${new Date(data.timestamp).toLocaleTimeString()}</span>
            </div>
            <p class="text-gray-800">${data.text}</p>
            ${data.confidence ? `<div class="text-xs text-gray-500 mt-1">Confidence: ${Math.round(data.confidence * 100)}%</div>` : ''}
        `;

        transcriptContainer.appendChild(transcriptElement);
        transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
    }

    displayFullTranscript(data) {
        const fullTranscriptContainer = document.getElementById('full-transcript');
        if (!fullTranscriptContainer) return;

        fullTranscriptContainer.innerHTML = `
            <div class="bg-white p-6 rounded-lg shadow-sm">
                <h3 class="text-lg font-semibold mb-4">Full Transcript</h3>
                <div class="prose max-w-none">
                    <pre class="whitespace-pre-wrap text-sm">${data.transcript}</pre>
                </div>
                
                ${data.speakers && data.speakers.length > 0 ? `
                    <div class="mt-6">
                        <h4 class="font-semibold mb-2">Speakers:</h4>
                        <div class="flex flex-wrap gap-2">
                            ${data.speakers.map(speaker => `
                                <span class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">${speaker}</span>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                ${data.speaker_statistics ? `
                    <div class="mt-6">
                        <h4 class="font-semibold mb-2">Speaker Statistics:</h4>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            ${Object.entries(data.speaker_statistics).map(([speaker, stats]) => `
                                <div class="bg-gray-50 p-4 rounded">
                                    <h5 class="font-medium">${speaker}</h5>
                                    <div class="text-sm text-gray-600 mt-2">
                                        <div>Words: ${stats.word_count}</div>
                                        <div>Speaking time: ${Math.round(stats.duration)}s</div>
                                        <div>Segments: ${stats.segments}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }

    async sendAudioChunk(audioBlob) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }

        try {
            // Convert to base64
            const base64Audio = await this.blobToBase64(audioBlob);
            
            const message = {
                type: 'audio_chunk',
                audio_data: base64Audio,
                chunk_index: this.chunkIndex++
            };

            this.ws.send(JSON.stringify(message));
        } catch (error) {
            console.error('Failed to send audio chunk:', error);
        }
    }

    blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            // Stop all tracks
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            
            this.updateUI('stopped');
            this.showSuccess('Recording stopped');
        }
    }

    pauseRecording() {
        if (this.mediaRecorder && this.isRecording) {
            if (this.mediaRecorder.state === 'recording') {
                this.mediaRecorder.pause();
                this.updateUI('paused');
                this.showSuccess('Recording paused');
            } else if (this.mediaRecorder.state === 'paused') {
                this.mediaRecorder.resume();
                this.updateUI('recording');
                this.showSuccess('Recording resumed');
            }
        }
    }

    async processRecording() {
        // Request full transcript
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'get_transcript' }));
        }
    }

    updateUI(state) {
        const recordBtn = document.getElementById('record-btn');
        const stopBtn = document.getElementById('stop-btn');
        const pauseBtn = document.getElementById('pause-btn');
        const statusIndicator = document.getElementById('status-indicator');

        switch (state) {
            case 'recording':
                if (recordBtn) recordBtn.classList.add('hidden');
                if (stopBtn) stopBtn.classList.remove('hidden');
                if (pauseBtn) pauseBtn.classList.remove('hidden');
                if (statusIndicator) {
                    statusIndicator.className = 'w-3 h-3 bg-red-500 rounded-full animate-pulse';
                    statusIndicator.textContent = 'Recording';
                }
                break;
                
            case 'paused':
                if (pauseBtn) {
                    pauseBtn.innerHTML = '<i class="fas fa-play"></i> Resume';
                    pauseBtn.classList.remove('bg-yellow-500');
                    pauseBtn.classList.add('bg-green-500');
                }
                if (statusIndicator) {
                    statusIndicator.className = 'w-3 h-3 bg-yellow-500 rounded-full';
                    statusIndicator.textContent = 'Paused';
                }
                break;
                
            case 'stopped':
                if (recordBtn) recordBtn.classList.remove('hidden');
                if (stopBtn) stopBtn.classList.add('hidden');
                if (pauseBtn) pauseBtn.classList.add('hidden');
                if (statusIndicator) {
                    statusIndicator.className = 'w-3 h-3 bg-gray-400 rounded-full';
                    statusIndicator.textContent = 'Ready';
                }
                break;
        }
    }

    navigateTo(page) {
        // Simple navigation - in a real app, use a router
        document.querySelectorAll('[data-page-content]').forEach(content => {
            content.classList.add('hidden');
        });
        
        const targetContent = document.querySelector(`[data-page-content="${page}"]`);
        if (targetContent) {
            targetContent.classList.remove('hidden');
        }

        // Update navigation
        document.querySelectorAll('[data-page]').forEach(link => {
            link.classList.remove('text-blue-600', 'font-semibold');
        });
        
        const activeLink = document.querySelector(`[data-page="${page}"]`);
        if (activeLink) {
            activeLink.classList.add('text-blue-600', 'font-semibold');
        }
    }

    updateLanguage(language) {
        localStorage.setItem('classmate_language', language);
        // In a real app, this would update the transcription language
    }

    showConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = status === 'Connected' ? 
                'text-green-600' : 'text-red-600';
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ClassMateWebApp();
});

// Export for potential module usage
export default ClassMateWebApp;
