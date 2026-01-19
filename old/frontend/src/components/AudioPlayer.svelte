<script>
  import { onMount, onDestroy } from 'svelte';
  import { transcriptSegments } from '../stores';
  import { formatTime } from '../utils';
  import { api } from '../api';

  export let conversationId;

  let audioElement;
  let isPlaying = false;
  let currentTime = 0;
  let duration = 0;
  let playbackSpeed = 1;
  let volume = 100;
  let isSeeking = false;
  let lastActiveSegmentId = null;

  onMount(() => {
    if (audioElement) {
      audioElement.src = `/api/audio/${conversationId}`;
      setupAudioListeners();
    }
  });

  onDestroy(() => {
    if (audioElement) {
      audioElement.pause();
    }
  });

  function setupAudioListeners() {
    // Set default playback rate to 1x
    audioElement.playbackRate = 1;
    
    audioElement.addEventListener('loadedmetadata', () => {
      duration = audioElement.duration;
      // Ensure playback rate is set after metadata loads
      audioElement.playbackRate = 1;
    });

    audioElement.addEventListener('timeupdate', () => {
      if (!isSeeking) {
        currentTime = audioElement.currentTime;
        scrollToCurrentSegment(audioElement.currentTime);
      }
    });

    audioElement.addEventListener('ended', () => {
      isPlaying = false;
    });
  }

  function togglePlayPause() {
    if (audioElement.paused) {
      audioElement.play();
      isPlaying = true;
    } else {
      audioElement.pause();
      isPlaying = false;
    }
  }

  function handleSeekStart() {
    isSeeking = true;
  }

  function handleSeek(e) {
    if (isSeeking) {
      currentTime = parseFloat(e.target.value);
      audioElement.currentTime = currentTime;
      scrollToCurrentSegment(currentTime);
      isSeeking = false;
    }
  }

  function handleSpeedChange(e) {
    playbackSpeed = parseFloat(e.target.value);
    audioElement.playbackRate = playbackSpeed;
  }

  function handleVolumeChange(e) {
    volume = e.target.value;
    audioElement.volume = volume / 100;
  }

  function scrollToCurrentSegment(currentTime) {
    const segments = $transcriptSegments;
    if (!segments || segments.length === 0) return;

    const buffer = 0.1;
    let activeSegment = null;

    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      if (currentTime >= seg.start_time && currentTime < (seg.end_time + buffer)) {
        activeSegment = i;
        break;
      }
    }

    if (activeSegment !== null) {
      const segmentId = `segment-${activeSegment}`;
      const segmentElement = document.getElementById(segmentId);

      if (segmentElement && segmentId !== lastActiveSegmentId) {
        if (lastActiveSegmentId) {
          const prevElement = document.getElementById(lastActiveSegmentId);
          if (prevElement) prevElement.classList.remove('active');
        }

        segmentElement.classList.add('active');
        lastActiveSegmentId = segmentId;

        const content = document.querySelector('.transcript-content');
        if (content) {
          const containerRect = content.getBoundingClientRect();
          const elementRect = segmentElement.getBoundingClientRect();

          const isVisible = (
            elementRect.top >= containerRect.top &&
            elementRect.bottom <= containerRect.bottom
          );

          if (!isVisible) {
            const elementOffsetTop = segmentElement.offsetTop;
            const containerHeight = content.clientHeight;
            const elementHeight = segmentElement.offsetHeight;
            const targetScrollTop = elementOffsetTop - (containerHeight / 2) + (elementHeight / 2);

            content.scrollTo({
              top: targetScrollTop,
              behavior: 'smooth'
            });
          }
        }
      }
    }
  }
</script>

<div class="audio-player-container">
  <audio bind:this={audioElement}></audio>
  <div class="audio-controls">
    <button class="control-btn" on:click={togglePlayPause}>
      {isPlaying ? '⏸' : '▶'}
    </button>
    <span>{formatTime(currentTime)}</span>
    <input
      type="range"
      min="0"
      max={duration || 100}
      value={currentTime}
      class="seek-bar"
      on:mousedown={handleSeekStart}
      on:mouseup={handleSeek}
      on:touchstart={handleSeekStart}
      on:touchend={handleSeek}
      on:change={handleSeek}
    />
    <span>{formatTime(duration)}</span>
    <select class="speed-select" bind:value={playbackSpeed} on:change={handleSpeedChange}>
      <option value={0.5}>0.5x</option>
      <option value={1}>1x</option>
      <option value={1.25}>1.25x</option>
      <option value={1.5}>1.5x</option>
      <option value={2}>2x</option>
    </select>
    <label for="volumeControl" class="volume-label">Volume:</label>
    <input
      type="range"
      id="volumeControl"
      min="0"
      max="100"
      value={volume}
      class="volume-slider"
      on:input={handleVolumeChange}
    />
  </div>
</div>

<style>
  .audio-player-container {
    margin-bottom: 2rem;
    padding: 1.5rem;
    background-color: var(--content-bg);
    border-radius: 8px;
    flex-shrink: 0;
  }

  .audio-player-container audio {
    display: none;
  }

  .audio-controls {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 1rem;
  }

  .control-btn {
    background: none;
    border: none;
    color: var(--text-primary);
    cursor: pointer;
    font-size: 1.5rem;
    padding: 0.5rem;
  }

  .seek-bar {
    flex: 1;
    height: 4px;
    background-color: var(--hover-bg);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .volume-label {
    color: var(--text-secondary);
    font-size: 0.9rem;
    white-space: nowrap;
  }

  .volume-slider {
    width: 100px;
    height: 4px;
    background-color: var(--hover-bg);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .speed-select {
    padding: 0.25rem 0.5rem;
    background-color: var(--hover-bg);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
  }
</style>
