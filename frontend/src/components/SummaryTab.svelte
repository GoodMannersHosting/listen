<script>
  import { onMount } from 'svelte';
  import { marked } from 'marked';
  import { escapeHtml } from '../utils';

  export let conversation;

  let summaryHtml = '';

  onMount(() => {
    if (conversation?.transcript?.summary) {
      renderSummary(conversation.transcript.summary);
    }
  });

  $: if (conversation?.transcript?.summary) {
    renderSummary(conversation.transcript.summary);
  }

  function renderSummary(summary) {
    if (!summary) {
      summaryHtml = '<p>No summary available.</p>';
      return;
    }

    try {
      marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        mangle: false
      });
      summaryHtml = marked.parse(summary);
    } catch (e) {
      console.error('Error rendering markdown:', e);
      summaryHtml = `<div class="markdown-content">${summary.replace(/\n/g, '<br>')}</div>`;
    }
  }
</script>

<div class="summary-content">
  {@html summaryHtml || '<p>No summary available.</p>'}
</div>

<style>
  /* CRITICAL: This fixes scrolling by constraining height and enabling overflow */
  .summary-content {
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
    border: 0px none rgba(0, 0, 0, 0);
    border-image: none;
  }

  .summary-content :global(h1),
  .summary-content :global(h2),
  .summary-content :global(h3),
  .summary-content :global(h4),
  .summary-content :global(h5),
  .summary-content :global(h6) {
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    font-weight: 600;
    color: var(--text-primary);
  }

  .summary-content :global(h1) { font-size: 1.75rem; }
  .summary-content :global(h2) { font-size: 1.5rem; }
  .summary-content :global(h3) { font-size: 1.25rem; }
  .summary-content :global(h4) { font-size: 1.1rem; }

  .summary-content :global(p) {
    margin-bottom: 1em;
  }

  .summary-content :global(ul),
  .summary-content :global(ol) {
    margin-bottom: 1em;
    padding-left: 2em;
  }

  .summary-content :global(li) {
    margin-bottom: 0.5em;
  }

  .summary-content :global(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5em 0;
  }

  .summary-content :global(table th),
  .summary-content :global(table td) {
    padding: 0.75rem;
    border: 1px solid var(--border-color);
    text-align: left;
  }

  .summary-content :global(table th) {
    background-color: var(--hover-bg);
    font-weight: 600;
  }

  .summary-content :global(code) {
    background-color: var(--hover-bg);
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
  }

  .summary-content :global(pre) {
    background-color: var(--hover-bg);
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    margin: 1em 0;
  }

  .summary-content :global(pre code) {
    background-color: transparent;
    padding: 0;
  }

  .summary-content :global(blockquote) {
    border-left: 4px solid var(--accent-color);
    padding-left: 1em;
    margin: 1em 0;
    color: var(--text-secondary);
    font-style: italic;
  }

  .summary-content :global(a) {
    color: var(--accent-color);
    text-decoration: none;
  }

  .summary-content :global(a:hover) {
    text-decoration: underline;
  }
</style>
