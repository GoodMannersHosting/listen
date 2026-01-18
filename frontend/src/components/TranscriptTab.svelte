<script>
  import { onMount } from 'svelte';
  import { transcriptSegments } from '../stores';
  import { api } from '../api';
  import { formatTime } from '../utils';

  export let conversation;

  let segments = [];

  onMount(async () => {
    if (conversation?.transcript) {
      await loadTranscript();
    }
  });

  $: if (conversation?.transcript) {
    loadTranscript();
  }

  async function loadTranscript() {
    if (conversation?.transcript?.segments) {
      segments = conversation.transcript.segments;
      transcriptSegments.set(segments);
    } else if (conversation?.id) {
      try {
        const segmentsResponse = await api.get(`/conversations/${conversation.id}/transcript/segments`);
        if (segmentsResponse) {
          segments = segmentsResponse;
          transcriptSegments.set(segments);
        }
      } catch (error) {
        console.error('Failed to load segments:', error);
      }
    }
  }
</script>

<div class="transcript-content">
  {#if segments.length > 0}
    {#each segments as segment, index}
      <div class="transcript-segment" id="segment-{index}" data-start-time={segment.start_time} data-end-time={segment.end_time}>
        <div class="segment-header">
          {#if segment.speaker_label}
            <span class="speaker-label">[{segment.speaker_label}]</span>
          {/if}
          <span class="timestamp">{formatTime(segment.start_time)} - {formatTime(segment.end_time)}</span>
        </div>
        <div class="segment-text">{segment.text}</div>
      </div>
    {/each}
  {:else if conversation?.transcript?.transcript_text}
    <p>{conversation.transcript.transcript_text}</p>
  {:else}
    <p>No transcript available.</p>
  {/if}
</div>

<style>
  /* CRITICAL: This fixes scrolling by constraining height and enabling overflow */
  .transcript-content {
    padding: 1.5rem;
    background-color: var(--content-bg);
    border-radius: 8px;
    line-height: 1.6;
    overflow-y: auto;
    overflow-x: hidden;
    flex: 1 1 0%;
    min-height: 0;
    height: 0; /* Critical flexbox trick for scrolling */
    max-height: 100%;
    position: relative;
    -webkit-overflow-scrolling: touch;
    box-sizing: border-box;
  }

  .transcript-segment {
    margin-bottom: 1rem;
    padding: 0.75rem 1rem;
    background-color: var(--hover-bg);
    border-radius: 6px;
    transition: background-color 0.4s ease, border-left 0.4s ease, box-shadow 0.4s ease, transform 0.4s ease;
    border-left: 3px solid transparent;
    display: block;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  }

  .transcript-segment:global(.active) {
    background-color: rgba(16, 163, 127, 0.2);
    border-left: 4px solid var(--accent-color);
    transform: scale(1.05);
    box-shadow: 0 2px 4px rgba(16, 163, 127, 0.2);
  }

  .segment-header {
    display: flex;
    align-items: center;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .segment-text {
    color: var(--text-primary);
    line-height: 1.6;
    font-size: 1rem;
    font-weight: 400;
    transition: font-size 0.4s ease, font-weight 0.4s ease;
  }

  .transcript-segment:global(.active) .segment-text {
    font-size: 1.2rem;
    font-weight: 700;
  }

  .speaker-label {
    font-weight: 600;
    color: var(--accent-color);
  }

  .timestamp {
    font-size: 0.85rem;
    color: var(--text-secondary);
    font-family: monospace;
  }
</style>
