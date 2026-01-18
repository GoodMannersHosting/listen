<script>
  import { currentProfile } from '../stores';
  import { api } from '../api';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  let fileInput;
  let dragover = false;
  let showOptions = false;
  let showProgress = false;
  let uploadProgress = 0;
  let progressText = 'Processing...';
  let selectedFile = null;
  let enableDiarization = false;
  let generateSummary = false;
  let generateActionItems = false;

  function handleDragOver(e) {
    e.preventDefault();
    dragover = true;
  }

  function handleDragLeave() {
    dragover = false;
  }

  function handleDrop(e) {
    e.preventDefault();
    dragover = false;
    if (e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  }

  function handleFileSelect(e) {
    if (e.target.files.length > 0) {
      handleFileSelection(e.target.files[0]);
    }
  }

  function handleFileSelection(file) {
    const allowedExtensions = ['.mp3', '.m4a', '.mp4', '.ogg', '.wav', '.flac'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(fileExt)) {
      alert('Unsupported file type. Please upload an audio file.');
      return;
    }

    selectedFile = file;
    showOptions = true;
  }

  async function uploadFile() {
    if (!$currentProfile) {
      alert('Please select a profile first');
      return;
    }

    if (!selectedFile) {
      alert('Please select a file');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('profile_id', $currentProfile.id);
    formData.append('diarization', enableDiarization);
    formData.append('generate_summary', generateSummary);
    formData.append('generate_action_items', generateActionItems);

    showOptions = false;
    showProgress = true;
    uploadProgress = 0;
    progressText = 'Uploading file...';

    try {
      const result = await api.uploadFile(formData, (percent) => {
        uploadProgress = percent;
        progressText = `Uploading file... ${percent}%`;
      });

      // Upload complete - transition to processing
      uploadProgress = 10;
      progressText = 'Upload complete. Initializing processing...';

      if (result.status === 'processing' && result.conversation_id) {
        // Start polling immediately with initial status
        pollJobStatus(result.conversation_id);
      } else if (result.conversation_id) {
        dispatch('conversationReady', { conversationId: result.conversation_id });
        showProgress = false;
      }
    } catch (error) {
      alert(error.message || 'Upload failed');
      showProgress = false;
    }
  }

  async function pollJobStatus(conversationId) {
    const maxAttempts = 300;
    let attempts = 0;

    const poll = async () => {
      try {
        const job = await api.get(`/conversations/${conversationId}/job`);
        
        // Update progress - ensure it's at least 10% if processing has started
        uploadProgress = Math.max(job.progress || 0, job.status === 'processing' ? 10 : 0);

        if (job.status === 'completed') {
          progressText = 'Processing complete!';
          uploadProgress = 100;
          // Small delay to show completion
          setTimeout(() => {
            dispatch('conversationReady', { conversationId });
            showProgress = false;
            // Refresh conversations list by dispatching event
            window.dispatchEvent(new CustomEvent('refreshConversations'));
          }, 500);
          return;
        } else if (job.status === 'failed') {
          progressText = `Processing failed: ${job.error || 'Unknown error'}`;
          alert(`Processing failed: ${job.error || 'Unknown error'}`);
          showProgress = false;
          return;
        } else if (job.status === 'pending') {
          // Job is still pending - show waiting message
          progressText = 'Waiting for processing to start...';
          uploadProgress = 10;
        } else {
          // Show detailed progress with chunk info if available
          if (job.total_chunks && job.current_chunk !== null && job.current_chunk !== undefined) {
            progressText = `Processing chunk ${job.current_chunk} of ${job.total_chunks}... (${uploadProgress}%)`;
          } else if (uploadProgress < 15) {
            progressText = `Preparing audio... (${uploadProgress}%)`;
          } else if (uploadProgress < 85) {
            progressText = `Transcribing audio... (${uploadProgress}%)`;
          } else if (uploadProgress < 100) {
            progressText = `Finalizing transcript${generateSummary || generateActionItems ? ' and generating content' : ''}... (${uploadProgress}%)`;
          } else {
            progressText = `Processing... (${uploadProgress}%)`;
          }
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 1000);
        } else {
          progressText = 'Processing is taking longer than expected. Please check back later.';
        }
      } catch (error) {
        console.error('Polling error:', error);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          progressText = 'Error checking processing status. Please refresh the page.';
        }
      }
    };

    // Start polling immediately
    poll();
  }
</script>

<div class="upload-area">
  <div class="upload-zone" class:dragover on:dragover={handleDragOver} on:dragleave={handleDragLeave} on:drop={handleDrop}>
    <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
      <polyline points="17 8 12 3 7 8"></polyline>
      <line x1="12" y1="3" x2="12" y2="15"></line>
    </svg>
    <h3>Upload Audio File</h3>
    <p>Drag and drop your audio file here, or click to browse</p>
    <input type="file" id="fileInput" accept="audio/*,.mp3,.m4a,.mp4,.ogg,.wav,.flac" on:change={handleFileSelect} hidden bind:this={fileInput}>
    <button class="btn-primary" on:click={() => fileInput?.click()}>Browse Files</button>

    {#if showOptions}
      <div class="upload-options">
        <label>
          <input type="checkbox" bind:checked={enableDiarization}> Enable Speaker Diarization
        </label>
        <label>
          <input type="checkbox" bind:checked={generateSummary}> Generate Summary
        </label>
        <label>
          <input type="checkbox" bind:checked={generateActionItems}> Generate Action Items
        </label>
        <button class="btn-primary" on:click={uploadFile}>Upload & Process</button>
      </div>
    {/if}

    {#if showProgress}
      <div class="upload-progress">
        <div class="progress-bar">
          <div class="progress-fill" style="width: {uploadProgress}%"></div>
        </div>
        <p>{progressText}</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .upload-area {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }

  .upload-zone {
    max-width: 600px;
    width: 100%;
    padding: 3rem;
    border: 2px dashed var(--border-color);
    border-radius: 8px;
    text-align: center;
    transition: border-color 0.3s;
  }

  .upload-zone.dragover {
    border-color: var(--accent-color);
    background-color: var(--hover-bg);
  }

  .upload-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto 1rem;
    color: var(--text-secondary);
  }

  .upload-zone h3 {
    margin-bottom: 0.5rem;
  }

  .upload-zone p {
    color: var(--text-secondary);
    margin-bottom: 1.5rem;
  }

  .upload-options {
    margin-top: 1.5rem;
    text-align: left;
  }

  .upload-options label {
    display: block;
    margin-bottom: 0.75rem;
    cursor: pointer;
  }

  .upload-options input[type="checkbox"] {
    margin-right: 0.5rem;
  }

  .upload-progress {
    margin-top: 1.5rem;
  }

  .progress-bar {
    width: 100%;
    height: 8px;
    background-color: var(--hover-bg);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background-color: var(--accent-color);
    transition: width 0.3s;
  }
</style>
