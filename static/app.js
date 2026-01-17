// Frontend JavaScript Application
const API_BASE = '/api';

// State management
let state = {
    currentProfile: null,
    profiles: [],
    conversations: [],
    currentConversation: null,
    audioPlayer: null,
    transcriptSegments: null
};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOMContentLoaded fired');
    try {
        console.log('Starting initialization...');
        await loadProfiles();
        console.log('Profiles loaded, setting up event listeners...');
        setupEventListeners();
        console.log('Event listeners set up, loading active profile...');
        loadActiveProfileFromStorage();
        console.log('Initialization complete');
    } catch (error) {
        console.error('Initialization error:', error);
        console.error('Error stack:', error.stack);
    }
});

// Also try loading profiles immediately if DOM is already loaded
if (document.readyState === 'loading') {
    console.log('DOM is still loading, waiting for DOMContentLoaded');
} else {
    console.log('DOM already loaded, initializing immediately');
    (async () => {
        try {
            await loadProfiles();
            setupEventListeners();
            loadActiveProfileFromStorage();
        } catch (error) {
            console.error('Immediate initialization error:', error);
        }
    })();
}

// Event Listeners
function setupEventListeners() {
    // Sidebar toggle
    document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);
    
    // Profile management
    document.getElementById('profileSelect').addEventListener('change', onProfileChange);
    document.getElementById('newProfileBtn').addEventListener('click', showProfileModal);
    document.getElementById('createProfileBtn').addEventListener('click', createProfile);
    document.getElementById('cancelProfileBtn').addEventListener('click', hideProfileModal);
    
    // Rename conversation
    document.getElementById('saveRenameBtn').addEventListener('click', renameConversation);
    document.getElementById('cancelRenameBtn').addEventListener('click', hideRenameModal);
    document.getElementById('renameModal').addEventListener('click', (e) => {
        if (e.target.id === 'renameModal') {
            hideRenameModal();
        }
    });
    document.getElementById('renameInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            renameConversation();
        } else if (e.key === 'Escape') {
            hideRenameModal();
        }
    });
    
    // Conversation management
    document.getElementById('newConversationBtn').addEventListener('click', showUploadArea);
    
    // File upload
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseBtn');
    
    browseBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', onFileSelected);
    
    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });
    
    document.getElementById('uploadBtn').addEventListener('click', uploadFile);
    
    // Tab navigation
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchTab(e.target.dataset.tab);
        });
    });
    
    // Audio player
    setupAudioPlayer();
}

// Profile Management
async function loadProfiles() {
    try {
        console.log('Loading profiles from:', `${API_BASE}/profiles`);
        const response = await fetch(`${API_BASE}/profiles`);
        console.log('Profile response status:', response.status, response.ok);
        
        if (!response.ok) {
            console.error('Failed to load profiles:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('Error response:', errorText);
            return;
        }
        
        const responseText = await response.text();
        console.log('Raw response text:', responseText);
        
        try {
            state.profiles = JSON.parse(responseText);
            console.log('Parsed profiles:', state.profiles);
        } catch (parseError) {
            console.error('Failed to parse profiles JSON:', parseError);
            console.error('Response text was:', responseText);
            return;
        }
        
        const select = document.getElementById('profileSelect');
        if (!select) {
            console.error('Profile select element not found');
            return;
        }
        
        select.innerHTML = '<option value="">Select Profile...</option>';
        if (state.profiles && state.profiles.length > 0) {
            console.log(`Adding ${state.profiles.length} profiles to select`);
            state.profiles.forEach(profile => {
                const option = document.createElement('option');
                option.value = profile.id;
                option.textContent = profile.display_name || profile.name;
                select.appendChild(option);
                console.log('Added profile option:', profile.display_name || profile.name, 'ID:', profile.id);
            });
            console.log('Profile select now has', select.options.length, 'options');
        } else {
            console.log('No profiles found in response');
        }
    } catch (error) {
        console.error('Failed to load profiles:', error);
        console.error('Error stack:', error.stack);
    }
}

function loadActiveProfileFromStorage() {
    console.log('loadActiveProfileFromStorage called, profiles:', state.profiles);
    const stored = localStorage.getItem('activeProfileId');
    const select = document.getElementById('profileSelect');
    
    if (!select) {
        console.error('Profile select not found in loadActiveProfileFromStorage');
        return;
    }
    
    if (stored && state.profiles && state.profiles.length > 0) {
        const profile = state.profiles.find(p => p.id === parseInt(stored));
        if (profile) {
            console.log('Loading stored profile:', profile);
            select.value = stored;
            onProfileChange({ target: { value: stored } });
        }
    } else if (state.profiles && state.profiles.length > 0) {
        // Select first profile by default
        const firstProfile = state.profiles[0];
        console.log('Selecting first profile by default:', firstProfile);
        select.value = firstProfile.id;
        onProfileChange({ target: { value: firstProfile.id.toString() } });
    } else {
        console.log('No profiles available to select');
    }
}

async function onProfileChange(e) {
    const profileId = parseInt(e.target.value);
    if (profileId) {
        state.currentProfile = state.profiles.find(p => p.id === profileId);
        localStorage.setItem('activeProfileId', profileId.toString());
        await loadConversations(profileId);
    } else {
        state.currentProfile = null;
        localStorage.removeItem('activeProfileId');
    }
}

function showProfileModal() {
    document.getElementById('profileModal').style.display = 'flex';
}

function hideProfileModal() {
    document.getElementById('profileModal').style.display = 'none';
    document.getElementById('profileNameInput').value = '';
    document.getElementById('profileDisplayNameInput').value = '';
}

async function createProfile() {
    const name = document.getElementById('profileNameInput').value.trim();
    const displayName = document.getElementById('profileDisplayNameInput').value.trim();
    
    if (!name) {
        alert('Profile name is required');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/profiles`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, display_name: displayName || null })
        });
        
        if (response.ok) {
            await loadProfiles();
            const newProfile = await response.json();
            document.getElementById('profileSelect').value = newProfile.id;
            onProfileChange({ target: { value: newProfile.id.toString() } });
            hideProfileModal();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to create profile');
        }
    } catch (error) {
        console.error('Failed to create profile:', error);
        alert('Failed to create profile');
    }
}

// Conversation Management
async function loadConversations(profileId) {
    try {
        const response = await fetch(`${API_BASE}/conversations?profile_id=${profileId}`);
        state.conversations = await response.json();
        renderConversations();
    } catch (error) {
        console.error('Failed to load conversations:', error);
    }
}

function renderConversations() {
    const list = document.getElementById('conversationsList');
    list.innerHTML = '';
    
    state.conversations.forEach(conv => {
        const item = document.createElement('div');
        item.className = 'conversation-item';
        
        const info = document.createElement('div');
        info.className = 'conversation-info';
        info.addEventListener('click', (e) => {
            // Don't trigger if clicking on action buttons
            if (!e.target.closest('.conversation-actions')) {
                loadConversation(conv.id);
            }
        });
        
        const title = document.createElement('div');
        title.className = 'conversation-title';
        title.textContent = conv.title || `Conversation ${conv.id}`;
        
        const time = document.createElement('div');
        time.className = 'conversation-time';
        time.textContent = formatDate(conv.created_at);
        
        info.appendChild(title);
        info.appendChild(time);
        
        const actions = document.createElement('div');
        actions.className = 'conversation-actions';
        
        const renameBtn = document.createElement('button');
        renameBtn.className = 'conversation-action-btn';
        renameBtn.innerHTML = '✏️';
        renameBtn.title = 'Rename';
        renameBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            showRenameModal(conv);
        });
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'conversation-action-btn delete';
        deleteBtn.innerHTML = '🗑️';
        deleteBtn.title = 'Delete';
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteConversation(conv.id);
        });
        
        actions.appendChild(renameBtn);
        actions.appendChild(deleteBtn);
        
        item.appendChild(info);
        item.appendChild(actions);
        list.appendChild(item);
    });
}

async function loadConversation(conversationId) {
    try {
        const response = await fetch(`${API_BASE}/conversations/${conversationId}`);
        const conversation = await response.json();
        
        state.currentConversation = conversation;
        
        // Update UI
        document.getElementById('uploadArea').style.display = 'none';
        document.getElementById('conversationContent').style.display = 'block';
        
        document.getElementById('conversationTitle').textContent = conversation.title || `Conversation ${conversationId}`;
        
        // Mark active conversation
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
            const title = item.querySelector('.conversation-title')?.textContent;
            const convTitle = conversation.title || `Conversation ${conversationId}`;
            if (title === convTitle || title === `Conversation ${conversationId}`) {
                item.classList.add('active');
            }
        });
        
        // Load transcript with segments
        if (conversation.transcript) {
            try {
                const segmentsResponse = await fetch(`${API_BASE}/conversations/${conversationId}/transcript/segments`);
                if (segmentsResponse.ok) {
                    conversation.transcript.segments = await segmentsResponse.json();
                }
            } catch (error) {
                console.error('Failed to load segments:', error);
            }
            await renderTranscript(conversation.transcript);
            setupAudioPlayer(conversationId);
            
            // Load summary and action items if available
            if (conversation.transcript.summary) {
                renderSummary(conversation.transcript.summary);
            }
            if (conversation.transcript.action_items) {
                renderActionItems(conversation.transcript.action_items);
            }
        }
        
        // Show/hide tabs based on available data
        if (conversation.transcript?.summary) {
            document.getElementById('summaryTab').style.display = 'inline-block';
            document.querySelector('[data-tab="summary"]').style.display = 'inline-block';
        }
        
        if (conversation.transcript?.action_items) {
            document.getElementById('actionItemsTab').style.display = 'inline-block';
            document.querySelector('[data-tab="actionItems"]').style.display = 'inline-block';
        }
        
        switchTab('transcript');
    } catch (error) {
        console.error('Failed to load conversation:', error);
    }
}

// File Upload
function onFileSelected(e) {
    if (e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
    }
}

function handleFileSelection(file) {
    // Validate file type
    const allowedTypes = ['audio/mpeg', 'audio/mp4', 'audio/ogg', 'audio/wav', 'audio/flac', 'audio/x-m4a'];
    const allowedExtensions = ['.mp3', '.m4a', '.mp4', '.ogg', '.wav', '.flac'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExt)) {
        alert('Unsupported file type. Please upload an audio file.');
        return;
    }
    
    // Show upload options
    document.getElementById('uploadOptions').style.display = 'block';
    document.getElementById('fileInput').files = file;
}

async function uploadFile() {
    if (!state.currentProfile) {
        alert('Please select a profile first');
        return;
    }
    
    const fileInput = document.getElementById('fileInput');
    if (!fileInput.files.length) {
        alert('Please select a file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('profile_id', state.currentProfile.id);
    formData.append('diarization', document.getElementById('enableDiarization').checked);
    formData.append('generate_summary', document.getElementById('generateSummary').checked);
    formData.append('generate_action_items', document.getElementById('generateActionItems').checked);
    
    // Show progress and initialize progress bar
    document.getElementById('uploadOptions').style.display = 'none';
    document.getElementById('uploadProgress').style.display = 'block';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = 'Uploading file...';
    
    try {
        // Use XMLHttpRequest for upload progress tracking
        const xhr = new XMLHttpRequest();
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                document.getElementById('progressFill').style.width = `${percentComplete}%`;
                document.getElementById('progressText').textContent = `Uploading file... ${percentComplete}%`;
            }
        });
        
        // Create a promise to handle the response
        let result;
        const response = await new Promise((resolve, reject) => {
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        result = JSON.parse(xhr.responseText);
                        resolve({
                            ok: true,
                            json: async () => result
                        });
                    } catch (e) {
                        reject(new Error('Failed to parse response'));
                    }
                } else {
                    let errorDetail = 'Upload failed';
                    try {
                        const errorData = JSON.parse(xhr.responseText);
                        errorDetail = errorData.detail || errorDetail;
                    } catch {
                        errorDetail = xhr.statusText || errorDetail;
                    }
                    reject(new Error(errorDetail));
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Network error'));
            });
            
            xhr.open('POST', `${API_BASE}/upload`);
            xhr.send(formData);
        });
        
        if (response.ok) {
            // Upload complete, immediately update UI to show processing has started
            document.getElementById('progressFill').style.width = '5%';
            document.getElementById('progressText').textContent = 'Upload complete. Starting processing...';
            
            // Small delay to show the message, then start polling
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Reload conversations
            await loadConversations(state.currentProfile.id);
            
            if (result && result.status === 'processing' && result.conversation_id) {
                // Show processing message and start polling immediately
                document.getElementById('progressFill').style.width = '5%';
                document.getElementById('progressText').textContent = 'Processing audio... This may take a few minutes.';
                
                // Start polling for job status immediately (don't await, let it run)
                console.log('Starting to poll for job status, conversation_id:', result.conversation_id);
                pollJobStatus(result.conversation_id).catch(err => {
                    console.error('Error in pollJobStatus:', err);
                });
            } else {
                console.log('Result:', result, 'Status:', result?.status, 'Conversation ID:', result?.conversation_id);
                // Already completed (shouldn't happen with async, but handle it)
                await loadConversation(result.conversation_id);
                document.getElementById('progressText').textContent = 'Processing complete!';
                document.getElementById('uploadProgress').style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Upload failed:', error);
        alert(error.message || 'Upload failed');
        document.getElementById('uploadProgress').style.display = 'none';
    } finally {
        document.getElementById('fileInput').value = '';
    }
}

async function pollJobStatus(conversationId) {
    const maxAttempts = 300; // 5 minutes max (1 second intervals)
    let attempts = 0;
    
    const poll = async () => {
        try {
            const response = await fetch(`${API_BASE}/conversations/${conversationId}/job`);
            if (response.ok) {
                const job = await response.json();
                
                // Update progress bar
                const progressFill = document.getElementById('progressFill');
                const progressText = document.getElementById('progressText');
                const progress = job.progress || 0;
                
                if (progressFill) {
                    progressFill.style.width = `${progress}%`;
                }
                
                if (job.status === 'completed') {
                    // Processing complete, reload conversation
                    if (progressText) {
                        progressText.textContent = 'Processing complete!';
                    }
                    if (progressFill) {
                        progressFill.style.width = '100%';
                    }
                    await loadConversation(conversationId);
                    document.getElementById('uploadProgress').style.display = 'none';
                    
                    // If summary was generated, automatically switch to summary tab
                    if (state.currentConversation?.transcript?.summary) {
                        // Small delay to ensure UI is ready
                        setTimeout(() => {
                            switchTab('summary');
                        }, 500);
                    }
                    return;
                } else if (job.status === 'failed') {
                    // Processing failed
                    if (progressText) {
                        progressText.textContent = `Processing failed: ${job.error || 'Unknown error'}`;
                    }
                    alert(`Processing failed: ${job.error || 'Unknown error'}`);
                    document.getElementById('uploadProgress').style.display = 'none';
                    return;
                } else if (job.status === 'processing' || job.status === 'pending') {
                    // Still processing, update progress text
                    if (progressText) {
                        const statusMessages = {
                            5: 'Starting processing...',
                            10: 'Analyzing audio file...',
                            15: 'Splitting audio into chunks...',
                            80: 'Transcribing audio...',
                            85: 'Saving transcript...',
                            87: 'Generating summary...',
                            92: 'Extracting action items...',
                            97: 'Finalizing...'
                        };
                        
                        // Find the closest status message
                        let message = `Processing... ${progress}%`;
                        for (const [threshold, msg] of Object.entries(statusMessages).sort((a, b) => b[0] - a[0])) {
                            if (progress >= parseInt(threshold)) {
                                message = `${msg} (${progress}%)`;
                                break;
                            }
                        }
                        progressText.textContent = message;
                    }
                    
                    // Check if summary is available yet (might be generated before job completes)
                    if (job.transcript_id) {
                        try {
                            const transcriptResponse = await fetch(`${API_BASE}/conversations/${conversationId}/transcript`);
                            if (transcriptResponse.ok) {
                                const transcript = await transcriptResponse.json();
                                if (transcript.summary && !state.currentConversation?.transcript?.summary) {
                                    // Summary just became available, reload conversation and switch to summary tab
                                    await loadConversation(conversationId);
                                    setTimeout(() => {
                                        switchTab('summary');
                                    }, 300);
                                }
                            }
                        } catch (e) {
                            // Ignore errors checking for summary
                        }
                    }
                    
                    // Continue polling
                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(poll, 1000); // Poll every second
                    } else {
                        if (progressText) {
                            progressText.textContent = 'Processing is taking longer than expected. Please check back later.';
                        }
                    }
                }
            } else {
                // Job not found yet, keep polling
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(poll, 1000);
                } else {
                    console.error(`Job status polling timed out for conversation ${conversationId}`);
                    const progressText = document.getElementById('progressText');
                    if (progressText) {
                        progressText.textContent = 'Processing timed out. Please check back later.';
                    }
                    document.getElementById('uploadProgress').style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error polling job status:', error);
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 2000); // Retry after 2 seconds on error
            } else {
                const progressText = document.getElementById('progressText');
                if (progressText) {
                    progressText.textContent = 'Error checking processing status. Please refresh the page.';
                }
            }
        }
    };
    
    // Start polling
    poll();
}

function showUploadArea() {
    document.getElementById('uploadArea').style.display = 'flex';
    document.getElementById('conversationContent').style.display = 'none';
    state.currentConversation = null;
}

// Transcript Rendering
async function renderTranscript(transcript) {
    const content = document.getElementById('transcriptContent');
    
    if (transcript.segments && transcript.segments.length > 0) {
        // Render with segments
        content.innerHTML = '';
        transcript.segments.forEach((seg, index) => {
            const segmentDiv = document.createElement('div');
            segmentDiv.className = 'transcript-segment';
            segmentDiv.id = `segment-${index}`;
            segmentDiv.dataset.startTime = seg.start_time;
            segmentDiv.dataset.endTime = seg.end_time;
            
            if (seg.speaker_label) {
                const speaker = document.createElement('span');
                speaker.className = 'speaker-label';
                speaker.textContent = `[${seg.speaker_label}]`;
                segmentDiv.appendChild(speaker);
            }
            
            const timestamp = document.createElement('span');
            timestamp.className = 'timestamp';
            timestamp.textContent = formatTime(seg.start_time) + ' - ' + formatTime(seg.end_time);
            segmentDiv.appendChild(timestamp);
            
            const text = document.createElement('span');
            text.textContent = seg.text;
            segmentDiv.appendChild(text);
            
            content.appendChild(segmentDiv);
        });
        
        // Store segments for quick lookup
        state.transcriptSegments = transcript.segments;
    } else {
        // Render plain text
        content.innerHTML = `<p>${transcript.transcript_text.replace(/\n/g, '<br>')}</p>`;
        state.transcriptSegments = null;
    }
}

function renderSummary(summary) {
    const content = document.getElementById('summaryContent');
    if (!summary) {
        content.innerHTML = '<p>No summary available.</p>';
        return;
    }
    
    // Use marked.js to render markdown if available, otherwise fallback to simple rendering
    if (typeof marked !== 'undefined') {
        try {
            // Configure marked for better rendering
            marked.setOptions({
                breaks: true,
                gfm: true,
                headerIds: false,
                mangle: false
            });
            content.innerHTML = marked.parse(summary);
        } catch (e) {
            console.error('Error rendering markdown:', e);
            // Fallback to simple rendering
            content.innerHTML = `<div class="markdown-content">${escapeHtml(summary).replace(/\n/g, '<br>')}</div>`;
        }
    } else {
        // Fallback if marked.js is not loaded
        content.innerHTML = `<div class="markdown-content">${escapeHtml(summary).replace(/\n/g, '<br>')}</div>`;
    }
    
    // Automatically switch to summary tab when summary is rendered
    const summaryTab = document.getElementById('summaryTab');
    if (summaryTab && !summaryTab.classList.contains('active')) {
        switchTab('summary');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderActionItems(actionItems) {
    const content = document.getElementById('actionItemsContent');
    content.innerHTML = '';
    
    actionItems.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'action-item';
        
        const title = document.createElement('h4');
        title.textContent = item.action || 'Action item';
        itemDiv.appendChild(title);
        
        const meta = document.createElement('div');
        meta.className = 'action-item-meta';
        meta.innerHTML = `
            <strong>Assignee:</strong> ${item.assignee || 'Unassigned'} |
            <strong>Priority:</strong> ${item.priority || 'Medium'} |
            <strong>Deadline:</strong> ${item.deadline || 'Not specified'}
        `;
        itemDiv.appendChild(meta);
        
        content.appendChild(itemDiv);
    });
}

// Tab Navigation
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });
    
    // Update tab panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
        if (pane.id === `${tabName}Tab`) {
            pane.classList.add('active');
        }
    });
    
    // Load content if needed
    if (tabName === 'summary' && state.currentConversation?.transcript?.summary) {
        renderSummary(state.currentConversation.transcript.summary);
    } else if (tabName === 'actionItems' && state.currentConversation?.transcript?.action_items) {
        renderActionItems(state.currentConversation.transcript.action_items);
    }
}

// Audio Player
function setupAudioPlayer(conversationId) {
    const audioElement = document.getElementById('audioPlayer');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const seekBar = document.getElementById('seekBar');
    const currentTimeSpan = document.getElementById('currentTime');
    const durationSpan = document.getElementById('duration');
    const speedSelect = document.getElementById('playbackSpeed');
    const volumeControl = document.getElementById('volumeControl');
    const container = document.getElementById('audioPlayerContainer');
    
    if (!conversationId) {
        container.style.display = 'none';
        return;
    }
    
    audioElement.src = `${API_BASE}/audio/${conversationId}`;
    container.style.display = 'block';
    
    // Track if user is dragging the seek bar
    let isSeeking = false;
    
    // Play/Pause
    playPauseBtn.addEventListener('click', () => {
        if (audioElement.paused) {
            audioElement.play();
            playPauseBtn.textContent = '⏸';
        } else {
            audioElement.pause();
            playPauseBtn.textContent = '▶';
        }
    });
    
    // Update time display
    audioElement.addEventListener('loadedmetadata', () => {
        durationSpan.textContent = formatTime(audioElement.duration);
        seekBar.max = audioElement.duration;
    });
    
    // Only update seek bar when not being dragged by user
    audioElement.addEventListener('timeupdate', () => {
        if (!isSeeking) {
            currentTimeSpan.textContent = formatTime(audioElement.currentTime);
            seekBar.value = audioElement.currentTime;
            
            // Auto-scroll to current transcript segment
            scrollToCurrentSegment(audioElement.currentTime);
        }
    });
    
    // Seek handling - prevent feedback loop
    seekBar.addEventListener('mousedown', () => {
        isSeeking = true;
    });
    
    seekBar.addEventListener('mousemove', () => {
        if (isSeeking) {
            // Update current time display while dragging
            const seekTime = parseFloat(seekBar.value);
            currentTimeSpan.textContent = formatTime(seekTime);
        }
    });
    
    seekBar.addEventListener('mouseup', () => {
        if (isSeeking) {
            const seekTime = parseFloat(seekBar.value);
            audioElement.currentTime = seekTime;
            isSeeking = false;
            // Scroll to the segment at the seek position
            scrollToCurrentSegment(seekTime);
        }
    });
    
    // Handle touch events for mobile
    seekBar.addEventListener('touchstart', () => {
        isSeeking = true;
    });
    
    seekBar.addEventListener('touchmove', () => {
        if (isSeeking) {
            const seekTime = parseFloat(seekBar.value);
            currentTimeSpan.textContent = formatTime(seekTime);
            // Update scroll position while dragging
            scrollToCurrentSegment(seekTime);
        }
    });
    
    seekBar.addEventListener('touchend', () => {
        if (isSeeking) {
            const seekTime = parseFloat(seekBar.value);
            audioElement.currentTime = seekTime;
            isSeeking = false;
            // Scroll to the segment at the seek position
            scrollToCurrentSegment(seekTime);
        }
    });
    
    // Update scroll while dragging with mouse
    seekBar.addEventListener('mousemove', () => {
        if (isSeeking) {
            const seekTime = parseFloat(seekBar.value);
            // Update scroll position while dragging
            scrollToCurrentSegment(seekTime);
        }
    });
    
    // Fallback for keyboard navigation
    seekBar.addEventListener('change', () => {
        if (!isSeeking) {
            const seekTime = parseFloat(seekBar.value);
            audioElement.currentTime = seekTime;
            scrollToCurrentSegment(seekTime);
        }
    });
    
    // Playback speed
    speedSelect.addEventListener('change', (e) => {
        audioElement.playbackRate = parseFloat(e.target.value);
    });
    
    // Volume
    volumeControl.addEventListener('input', (e) => {
        audioElement.volume = e.target.value / 100;
    });
    
    audioElement.addEventListener('ended', () => {
        playPauseBtn.textContent = '▶';
    });
}

// Sidebar Toggle
function toggleSidebar(e) {
    if (e) {
        e.stopPropagation();
    }
    
    const sidebar = document.getElementById('sidebar');
    
    // Check if we're on mobile (sidebar uses 'open' class)
    const isMobile = window.innerWidth <= 768;
    
    if (isMobile) {
        // On mobile, toggle 'open' class for slide in/out
        sidebar.classList.toggle('open');
        // Remove collapsed class if present
        sidebar.classList.remove('collapsed');
    } else {
        // On desktop, toggle 'collapsed' class for width change
        sidebar.classList.toggle('collapsed');
        // Remove open class if present
        sidebar.classList.remove('open');
    }
}

// Handle window resize to sync sidebar state
window.addEventListener('resize', () => {
    const sidebar = document.getElementById('sidebar');
    const isMobile = window.innerWidth <= 768;
    
    if (isMobile) {
        // On mobile, use 'open' class, remove 'collapsed'
        if (sidebar.classList.contains('collapsed')) {
            sidebar.classList.remove('collapsed');
            sidebar.classList.add('open');
        }
    } else {
        // On desktop, use 'collapsed' class, remove 'open'
        if (sidebar.classList.contains('open') && !sidebar.classList.contains('collapsed')) {
            sidebar.classList.remove('open');
        }
    }
});

// Utility Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return 'Just now';
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Scroll to current transcript segment based on playback time
let lastActiveSegmentId = null;

function scrollToCurrentSegment(currentTime) {
    // Only scroll if we're on the transcript tab
    const transcriptTab = document.getElementById('transcriptTab');
    if (!transcriptTab || !transcriptTab.classList.contains('active')) {
        return;
    }
    
    const content = document.getElementById('transcriptContent');
    if (!content || !state.transcriptSegments) {
        return;
    }
    
    // Find the segment that contains the current time
    // Use a small buffer to prevent jumping ahead too early
    const buffer = 0.1; // 100ms buffer to stay on current segment
    let activeSegment = null;
    
    // First pass: find segments where currentTime is within the segment (with buffer)
    for (let i = 0; i < state.transcriptSegments.length; i++) {
        const seg = state.transcriptSegments[i];
        // Use buffer on end_time to prevent jumping ahead too early
        if (currentTime >= seg.start_time && currentTime < (seg.end_time + buffer)) {
            activeSegment = i;
            break;
        }
    }
    
    // If no match, find the most recent segment that hasn't fully passed
    if (activeSegment === null && state.transcriptSegments.length > 0) {
        // Look backwards from the end to find the most recent segment
        for (let i = state.transcriptSegments.length - 1; i >= 0; i--) {
            const seg = state.transcriptSegments[i];
            // If we've passed the start but not too far past the end (with buffer)
            if (currentTime >= seg.start_time && currentTime < (seg.end_time + buffer)) {
                activeSegment = i;
                break;
            }
        }
        
        // If still no match, find the closest upcoming segment
        if (activeSegment === null) {
            let closestIndex = null;
            let closestDistance = Infinity;
            
            for (let i = 0; i < state.transcriptSegments.length; i++) {
                const seg = state.transcriptSegments[i];
                if (seg.start_time > currentTime) {
                    const distance = seg.start_time - currentTime;
                    if (distance < closestDistance) {
                        closestDistance = distance;
                        closestIndex = i;
                    }
                }
            }
            
            // Only use upcoming segment if it's very close (within 0.5 seconds)
            if (closestIndex !== null && closestDistance < 0.5) {
                activeSegment = closestIndex;
            } else {
                // Otherwise, use the most recent segment that has passed
                for (let i = state.transcriptSegments.length - 1; i >= 0; i--) {
                    const seg = state.transcriptSegments[i];
                    if (currentTime >= seg.end_time) {
                        activeSegment = i;
                        break;
                    }
                }
            }
        }
        
        // Final fallback
        if (activeSegment === null) {
            activeSegment = 0;
        }
    }
    
    // Scroll to the active segment
    if (activeSegment !== null) {
        const segmentId = `segment-${activeSegment}`;
        const segmentElement = document.getElementById(segmentId);
        
        if (segmentElement && segmentId !== lastActiveSegmentId) {
            // Remove previous active class
            if (lastActiveSegmentId) {
                const prevElement = document.getElementById(lastActiveSegmentId);
                if (prevElement) {
                    prevElement.classList.remove('active');
                }
            }
            
            // Add active class to current segment
            segmentElement.classList.add('active');
            lastActiveSegmentId = segmentId;
            
            // Scroll into view within the transcript container (not the page)
            const containerRect = content.getBoundingClientRect();
            const elementRect = segmentElement.getBoundingClientRect();
            
            // Calculate if element is visible in container
            const isVisible = (
                elementRect.top >= containerRect.top &&
                elementRect.bottom <= containerRect.bottom
            );
            
            if (!isVisible) {
                // Only auto-scroll if user isn't manually scrolling
                // Check if scroll is near the bottom (user might be reading)
                const scrollBottom = content.scrollTop + content.clientHeight;
                const contentHeight = content.scrollHeight;
                const isNearBottom = (contentHeight - scrollBottom) < 100; // Within 100px of bottom
                
                // Calculate scroll position to center the element in the container
                const elementOffsetTop = segmentElement.offsetTop;
                const containerHeight = content.clientHeight;
                const elementHeight = segmentElement.offsetHeight;
                
                const targetScrollTop = elementOffsetTop - (containerHeight / 2) + (elementHeight / 2);
                
                // Only auto-scroll if not near bottom (user might be reading ahead)
                if (!isNearBottom || Math.abs(content.scrollTop - targetScrollTop) > 200) {
                    // Smooth scroll within the container
                    content.scrollTo({
                        top: targetScrollTop,
                        behavior: 'smooth'
                    });
                }
            }
        }
    }
}

// Rename Conversation
let currentRenameConversationId = null;

function showRenameModal(conversation) {
    currentRenameConversationId = conversation.id;
    const input = document.getElementById('renameInput');
    input.value = conversation.title || `Conversation ${conversation.id}`;
    document.getElementById('renameModal').style.display = 'flex';
    // Focus the input after modal is shown
    setTimeout(() => input.focus(), 100);
}

function hideRenameModal() {
    document.getElementById('renameModal').style.display = 'none';
    document.getElementById('renameInput').value = '';
    currentRenameConversationId = null;
}

async function renameConversation() {
    if (!currentRenameConversationId) return;
    
    const newTitle = document.getElementById('renameInput').value.trim();
    if (!newTitle) {
        alert('Title cannot be empty');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/conversations/${currentRenameConversationId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
        });
        
        if (response.ok) {
            await loadConversations(state.currentProfile.id);
            
            // If this is the currently open conversation, reload it
            if (state.currentConversation && state.currentConversation.id === currentRenameConversationId) {
                await loadConversation(currentRenameConversationId);
            }
            
            hideRenameModal();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to rename conversation');
        }
    } catch (error) {
        console.error('Failed to rename conversation:', error);
        alert('Failed to rename conversation');
    }
}

// Delete Conversation
async function deleteConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this conversation? This will permanently delete the audio file and all associated data.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
            method: 'DELETE'
        });
        
        if (response.ok || response.status === 204) {
            // If we deleted the currently open conversation, show upload area
            if (state.currentConversation && state.currentConversation.id === conversationId) {
                showUploadArea();
            }
            
            // Reload conversations
            await loadConversations(state.currentProfile.id);
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to delete conversation');
        }
    } catch (error) {
        console.error('Failed to delete conversation:', error);
        alert('Failed to delete conversation');
    }
}
