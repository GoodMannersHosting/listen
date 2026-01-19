<script>
  import { onMount } from 'svelte';
  import { currentConversation, transcriptSegments } from '../stores';
  import { api } from '../api';
  import AudioPlayer from './AudioPlayer.svelte';
  import TranscriptTab from './TranscriptTab.svelte';
  import SummaryTab from './SummaryTab.svelte';
  import ActionItemsTab from './ActionItemsTab.svelte';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  let activeTab = 'transcript';
  let conversation = null;

  onMount(() => {
    currentConversation.subscribe(conv => {
      conversation = conv;
      if (conv?.transcript?.summary) {
        // Auto-switch to summary tab when summary is available
        setTimeout(() => {
          activeTab = 'summary';
        }, 500);
      }
    });
  });

  function switchTab(tab) {
    activeTab = tab;
  }

  $: hasSummary = conversation?.transcript?.summary;
  $: hasActionItems = conversation?.transcript?.action_items;
</script>

{#if conversation}
  <div class="conversation-content">
    <div class="content-header">
      <h2>{conversation.title || `Conversation ${conversation.id}`}</h2>
      <div class="tab-navigation">
        <button class="tab-btn" class:active={activeTab === 'transcript'} on:click={() => switchTab('transcript')}>
          Transcript
        </button>
        {#if hasSummary}
          <button class="tab-btn" class:active={activeTab === 'summary'} on:click={() => switchTab('summary')}>
            Summary
          </button>
        {/if}
        {#if hasActionItems}
          <button class="tab-btn" class:active={activeTab === 'actionItems'} on:click={() => switchTab('actionItems')}>
            Action Items
          </button>
        {/if}
      </div>
    </div>

    {#if conversation.audio_file_path}
      <AudioPlayer conversationId={conversation.id} />
    {/if}

    <div class="tab-content">
      {#if activeTab === 'transcript'}
        <TranscriptTab conversation={conversation} />
      {:else if activeTab === 'summary'}
        <SummaryTab conversation={conversation} />
      {:else if activeTab === 'actionItems'}
        <ActionItemsTab conversation={conversation} />
      {/if}
    </div>
  </div>
{/if}

<style>
  .conversation-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 2rem;
    min-height: 0;
    overflow: hidden;
    height: 100%;
  }

  .content-header {
    margin-bottom: 1.5rem;
    flex-shrink: 0;
  }

  .content-header h2 {
    margin-bottom: 1rem;
  }

  .tab-navigation {
    display: flex;
    gap: 0.5rem;
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
  }

  .tab-btn {
    padding: 0.75rem 1.5rem;
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 0.9rem;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }

  .tab-btn:hover {
    color: var(--text-primary);
  }

  .tab-btn.active {
    color: var(--text-primary);
    border-bottom-color: var(--accent-color);
  }

  /* CRITICAL: This is where we fix scrolling */
  .tab-content {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative;
  }
</style>
