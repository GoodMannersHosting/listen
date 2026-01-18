<script>
  export let conversation;

  $: actionItems = conversation?.transcript?.action_items || [];
</script>

<div class="action-items-content">
  {#if actionItems.length > 0}
    {#each actionItems as item}
      <div class="action-item">
        <h4>{item.action || 'Action item'}</h4>
        <div class="action-item-meta">
          <strong>Assignee:</strong> {item.assignee || 'Unassigned'} |
          <strong>Priority:</strong> {item.priority || 'Medium'} |
          <strong>Deadline:</strong> {item.deadline || 'Not specified'}
        </div>
      </div>
    {/each}
  {:else}
    <p>No action items available.</p>
  {/if}
</div>

<style>
  /* CRITICAL: This fixes scrolling by constraining height and enabling overflow */
  .action-items-content {
    padding: 1.5rem;
    background-color: var(--content-bg);
    border-radius: 8px;
    line-height: 1.6;
    overflow-y: auto;
    overflow-x: hidden;
    flex: 1;
    min-height: 0;
    position: relative;
    -webkit-overflow-scrolling: touch;
  }

  .action-item {
    margin-bottom: 1rem;
    padding: 1rem;
    background-color: var(--hover-bg);
    border-left: 3px solid var(--accent-color);
    border-radius: 4px;
  }

  .action-item h4 {
    margin-bottom: 0.5rem;
  }

  .action-item-meta {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-top: 0.5rem;
  }
</style>
