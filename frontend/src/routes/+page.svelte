<script>
  import { onDestroy, onMount } from 'svelte';
  import { api } from '../api.js';
  import Markdown from 'svelte-exmarkdown';
  import { gfmPlugin } from 'svelte-exmarkdown/gfm';

  const markdownPlugins = [gfmPlugin()];

  let uploads = [];
  let current = null;
  let segments = [];
  let activeJobs = [];
  let activeJobsTimer = null;
  let jobStats = null;
  let statsTimer = null;
  let topJob = null;

  let prompts = [];
  let showPrompts = false;
  let editingPromptId = null;
  let editingPromptName = '';
  let editingPromptContent = '';
  let editingPromptIsDefault = false;

  let showReprocess = false;
  let reprocessSummarize = true;
  let reprocessActionItems = true;
  let reprocessBusy = false;

  let uploading = false;
  let error = '';
  let searchQuery = '';
  let searchTimer = null;

  function normalizeSummaryMarkdown(md) {
    if (!md) return md;
    // Some models emit HTML <br> inside otherwise-Markdown content.
    // Convert to real newlines so the markdown renderer formats it naturally.
    return md.replace(/<br\s*\/?>/gi, '\n');
  }

  function _toTitleCase(s) {
    return (s || '')
      .toString()
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (m) => m.toUpperCase());
  }

  function normalizeActionItems(ai) {
    // Returns an array of row objects.
    if (ai == null) return [];

    // Worker may store {"raw": "..."} when it can't parse JSON.
    if (typeof ai === 'object' && !Array.isArray(ai) && typeof ai.raw === 'string') {
      const raw = ai.raw.trim();
      if (raw.startsWith('[') || raw.startsWith('{')) {
        try {
          return normalizeActionItems(JSON.parse(raw));
        } catch {
          return [{ raw }];
        }
      }
      return [{ raw }];
    }

    if (Array.isArray(ai)) {
      return ai.map((x) => {
        if (x == null) return { item: '' };
        if (typeof x === 'string' || typeof x === 'number' || typeof x === 'boolean') return { item: String(x) };
        if (typeof x === 'object') return x;
        return { item: String(x) };
      });
    }

    if (typeof ai === 'object') {
      // Common shape: { items: [...] }
      if (Array.isArray(ai.items)) return normalizeActionItems(ai.items);
      return [ai];
    }

    return [{ item: String(ai) }];
  }

  function formatCell(v) {
    if (v == null) return '';
    if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return String(v);
    try {
      return JSON.stringify(v);
    } catch {
      return String(v);
    }
  }

  function columnsForRows(rows) {
    const preferred = [
      'title',
      'task',
      'action',
      'item',
      'owner',
      'assignee',
      'due',
      'due_date',
      'date',
      'priority',
      'status',
      'notes',
      'details'
    ];
    const seen = new Set();
    const cols = [];
    for (const k of preferred) {
      if (rows.some((r) => r && typeof r === 'object' && k in r)) {
        seen.add(k);
        cols.push(k);
      }
    }
    for (const r of rows) {
      if (!r || typeof r !== 'object') continue;
      for (const k of Object.keys(r)) {
        if (seen.has(k)) continue;
        seen.add(k);
        cols.push(k);
      }
    }
    // If everything was empty objects, fall back.
    return cols.length ? cols : ['item'];
  }

  $: actionRows = normalizeActionItems(current?.action_items);
  $: actionCols = columnsForRows(actionRows || []);
  $: summaryMd = normalizeSummaryMarkdown(current?.summary);
  $: topJobProgress = Math.max(0, Math.min(100, Number(topJob?.progress ?? 0)));
  $: showJobBar = !!topJob || (jobStats?.active ?? 0) > 0;

  async function refreshUploads() {
    uploads = await api.listUploads(searchQuery);
  }

  async function selectUpload(id) {
    current = await api.getUpload(id);
    segments = await api.getSegments(id);
  }

  function fmtDate(d) {
    return new Date(d).toLocaleString();
  }

  function fmtShort(d) {
    return new Date(d).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function fmtTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  async function refreshJobStats() {
    try {
      jobStats = await api.getJobStats();
    } catch (e) {
      // ignore
    }
  }

  async function refreshActiveJobs() {
    try {
      activeJobs = await api.listActiveJobs();
    } catch (e) {
      // ignore
    }
  }

  function getTopJob(jobs) {
    if (!jobs?.length) return null;
    // FIFO: show the oldest job first (created_at asc from the API).
    return jobs[0];
  }

  // IMPORTANT: in Svelte's reactive assignments, dependencies are determined statically.
  // Pass `activeJobs` explicitly so changes re-compute `topJob`.
  $: topJob = getTopJob(activeJobs);

  async function onUploadSubmit(e) {
    e.preventDefault();
    error = '';
    uploading = true;
    try {
      const fd = new FormData(e.target);
      const res = await api.createUpload(fd);
      // Update the top job banner ASAP (avoids "job finished before banner appeared").
      await refreshActiveJobs();

      await Promise.all([refreshUploads(), selectUpload(res.upload_id)]);
      e.target.reset();
    } catch (e) {
      error = e.message || 'Upload failed';
    } finally {
      uploading = false;
    }
  }

  async function renameCurrent() {
    if (!current) return;
    const name = prompt('Rename file', current.display_name);
    if (!name) return;
    await api.renameUpload(current.id, name.trim());
    await refreshUploads();
    await selectUpload(current.id);
  }

  function parseTagsInput(s) {
    const raw = (s || '').split(',').map((t) => t.trim()).filter(Boolean);
    const seen = new Set();
    const out = [];
    for (const t0 of raw) {
      const t = t0.toLowerCase();
      if (!t) continue;
      if (seen.has(t)) continue;
      seen.add(t);
      out.push(t);
      if (out.length >= 20) break;
    }
    return out;
  }

  let showTags = false;
  let tagsInput = '';
  let tagsBusy = false;

  function openTags() {
    if (!current) return;
    tagsInput = (current.tags || []).join(', ');
    showTags = true;
  }

  function closeTagsOnKeydown(e) {
    if (e.key === 'Escape') showTags = false;
  }

  async function saveTags() {
    if (!current) return;
    error = '';
    tagsBusy = true;
    try {
      const tags = parseTagsInput(tagsInput);
      await api.updateUpload(current.id, { tags });
      showTags = false;
      await refreshUploads();
      await selectUpload(current.id);
    } catch (e) {
      error = e.message || 'Saving tags failed';
    } finally {
      tagsBusy = false;
    }
  }

  function onSearchInput(e) {
    searchQuery = e.target.value;
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
      await refreshUploads();
    }, 200);
  }

  function openReprocess() {
    if (!current) return;
    // sensible defaults: if a field is missing, default to regenerating it
    reprocessSummarize = current.summary == null;
    reprocessActionItems = current.action_items == null;
    // if both already exist, default both checked (user can uncheck)
    if (!reprocessSummarize && !reprocessActionItems) {
      reprocessSummarize = true;
      reprocessActionItems = true;
    }
    showReprocess = true;
  }

  function closeReprocessOnKeydown(e) {
    if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
      showReprocess = false;
    }
  }

  async function submitReprocess() {
    if (!current) return;
    error = '';
    reprocessBusy = true;
    try {
      await api.reprocessUpload(current.id, {
        summarize: !!reprocessSummarize,
        action_items: !!reprocessActionItems
      });
      showReprocess = false;
      await refreshActiveJobs();
      await refreshJobStats();
    } catch (e) {
      error = e.message || 'Re-process failed';
    } finally {
      reprocessBusy = false;
    }
  }

  async function deleteUpload(u) {
    if (!confirm(`Delete \"${u.display_name}\"?`)) return;
    await api.deleteUpload(u.id);
    if (current?.id === u.id) {
      current = null;
      segments = [];
    }
    await refreshUploads();
  }

  function closePromptsOnKeydown(e) {
    if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
      showPrompts = false;
    }
  }

  async function openPrompts() {
    prompts = await api.listPrompts();
    showPrompts = true;
  }

  function editPrompt(p) {
    editingPromptId = p.id;
    editingPromptName = p.name;
    editingPromptContent = p.content;
    editingPromptIsDefault = p.is_default;
  }

  async function savePrompt() {
    if (!editingPromptId) return;
    await api.updatePrompt(editingPromptId, {
      name: editingPromptName,
      content: editingPromptContent,
      is_default: editingPromptIsDefault
    });
    prompts = await api.listPrompts();
  }

  onMount(async () => {
    await refreshUploads();
    await refreshJobStats();
    await refreshActiveJobs();

    statsTimer = setInterval(refreshJobStats, 2000);
    activeJobsTimer = setInterval(async () => {
      await refreshActiveJobs();
      await refreshUploads();
      // Best-effort refresh of the currently open item, without stealing focus.
      if (current?.id) {
        await selectUpload(current.id);
      }
    }, 1000);
  });

  onDestroy(() => {
    if (activeJobsTimer) clearInterval(activeJobsTimer);
    if (statsTimer) clearInterval(statsTimer);
    if (searchTimer) clearTimeout(searchTimer);
  });
</script>

<div class="layout">
  <aside class="sidebar">
    <div class="sidebarHeader">
      <div class="sidebarHeaderLeft">
        <div class="title">Listen</div>
        <div class="queuePill" title="Queued + processing">
          Jobs in queue: {jobStats?.active ?? 0}
        </div>
      </div>
      <button class="btn" on:click={openPrompts}>Prompts</button>
    </div>

    <form class="uploadForm" on:submit={onUploadSubmit}>
      <label class="label" for="fileInput">Upload audio</label>
      <input id="fileInput" class="input" name="file" type="file" accept="audio/*" required />

      <div class="row">
        <label class="check"><input type="checkbox" name="summarize" value="true" /> Summarize</label>
        <label class="check"><input type="checkbox" name="action_items" value="true" /> Action items</label>
      </div>

      <input class="input" name="display_name" placeholder="Name (optional)" />
      <input class="input" name="llm_model" placeholder="LLM model (optional)" />

      <button class="btn primary" disabled={uploading}>
        {uploading ? 'Uploading…' : 'Upload & queue'}
      </button>

      {#if error}
        <div class="error">{error}</div>
      {/if}
    </form>

    <div class="list">
      <div class="listHeaderRow">
        <div class="listHeader">Library</div>
        <input
          class="input search"
          placeholder="Search name or tag…"
          value={searchQuery}
          on:input={onSearchInput}
        />
      </div>
      {#each uploads as u}
        <div class="item" class:active={current?.id === u.id}>
          <button class="itemMain" on:click={() => selectUpload(u.id)}>
            <div class="itemName">{u.display_name}</div>
            <div class="itemMeta muted">{fmtDate(u.created_at)}</div>
            {#if u.tags?.length}
              <div class="tagRow">
                {#each u.tags.slice(0, 4) as t}
                  <span class="tag">{t}</span>
                {/each}
                {#if u.tags.length > 4}
                  <span class="muted">+{u.tags.length - 4}</span>
                {/if}
              </div>
            {/if}
          </button>
          <button class="btn danger" on:click={() => deleteUpload(u)}>Del</button>
        </div>
      {/each}
    </div>
  </aside>

  <main class="main">
    {#if showJobBar}
      <div class="jobBar">
        {#if topJob}
          <div class="jobTop">
            <div>
              <strong>Job:</strong>
              {uploads.find((u) => u.id === topJob.upload_id)?.display_name ?? `Upload #${topJob.upload_id}`}
              {#if activeJobs.length > 1}
                <span class="muted" style="margin-left: 8px">({activeJobs.length} jobs)</span>
              {/if}
            </div>
            <div class="muted">
              {#if topJob.started_at}
                Started {fmtShort(topJob.started_at)}
              {:else}
                Queued {fmtShort(topJob.created_at)}
              {/if}
            </div>
          </div>
          <div>
            <strong>Status:</strong> {topJob.status} {topJob.phase ? `(${topJob.phase})` : ''}
          </div>
          <div class="muted">
            {topJob.current_chunk ?? 0}/{topJob.total_chunks ?? 0} · {topJob.progress}%
          </div>
        {:else}
          <div class="jobTop">
            <div>
              <strong>Job:</strong> {jobStats?.active ?? 0} active
            </div>
            <div class="muted">Loading details…</div>
          </div>
          <div class="muted">Fetching job status…</div>
        {/if}

        <div class="progress" aria-label="Job progress">
          <div
            class="progressFill"
            class:indeterminate={!topJob || (topJob.status === 'queued' && topJobProgress === 0)}
            style={`width:${!topJob ? 35 : topJobProgress === 0 && topJob.status === 'queued' ? 35 : topJobProgress}%`}
          ></div>
        </div>

        {#if topJob?.error}
          <div class="error">{topJob.error}</div>
        {/if}
      </div>
    {/if}

    {#if current}
      <div class="header">
        <div>
          <div class="h1">{current.display_name}</div>
          <div class="muted">{current.original_filename}</div>
        </div>
        <div class="headerActions">
          <button class="btn" on:click={openReprocess}>Re-process</button>
          <button class="btn" on:click={openTags}>Tags</button>
          <button class="btn" on:click={renameCurrent}>Rename</button>
          <a class="btn" href={`/api/uploads/${current.id}/audio`} target="_blank" rel="noreferrer">Audio</a>
        </div>
      </div>

      <div class="panel">
        <audio controls style="width: 100%" src={`/api/uploads/${current.id}/audio`}></audio>
      </div>

      <div class="panel">
        <div class="panelTitle">Action items</div>
        {#if actionRows?.length}
          <div class="tableWrap">
            <table class="aiTable">
              <thead>
                <tr>
                  {#each actionCols as c}
                    <th>{_toTitleCase(c)}</th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each actionRows as r}
                  <tr>
                    {#each actionCols as c}
                      <td>{formatCell(r?.[c])}</td>
                    {/each}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else}
          <div class="muted">No action items.</div>
        {/if}
      </div>

      <div class="grid">
        <section class="panel">
          <div class="panelTitle">Transcript</div>
          {#if segments.length}
            <div class="segments">
              {#each segments as s}
                <div class="seg">
                  <div class="segMeta muted">{fmtTime(s.start_time)}–{fmtTime(s.end_time)}</div>
                  <div>{s.text}</div>
                </div>
              {/each}
            </div>
          {:else if current.transcript_text}
            <pre class="pre">{current.transcript_text}</pre>
          {:else}
            <div class="muted">No transcript yet.</div>
          {/if}
        </section>

        <section class="panel">
          <div class="panelTitle">Summary</div>
          {#if current.summary}
            <div class="markdown">
              <Markdown md={summaryMd} plugins={markdownPlugins} />
            </div>
          {:else}
            <div class="muted">No summary.</div>
          {/if}
        </section>
      </div>
    {:else}
      <div class="empty">
        <div class="h1">Upload audio to begin</div>
        <div class="muted">Files are queued in RabbitMQ and processed by the worker.</div>
      </div>
    {/if}
  </main>
</div>

{#if showPrompts}
  <div
    class="modalBackdrop"
    role="button"
    tabindex="0"
    on:keydown={closePromptsOnKeydown}
    on:click|self={() => (showPrompts = false)}
  >
    <div class="modal" role="dialog" aria-modal="true" aria-label="Prompts editor">
      <div class="modalHeader">
        <div class="h2">Prompts</div>
        <button class="btn" on:click={() => (showPrompts = false)}>Close</button>
      </div>
      <div class="modalBody">
        <div class="promptList">
          {#each prompts as p}
            <button class="promptItem" on:click={() => editPrompt(p)}>
              <div><strong>{p.kind}</strong> {p.is_default ? '(default)' : ''}</div>
              <div class="muted">{p.name}</div>
            </button>
          {/each}
        </div>

        {#if editingPromptId}
          <div class="promptEditor">
            <label class="label" for="promptNameInput">Name</label>
            <input id="promptNameInput" class="input" bind:value={editingPromptName} />

            <label class="check" style="margin-top: 8px">
              <input type="checkbox" bind:checked={editingPromptIsDefault} />
              Default for this kind
            </label>

            <label class="label" for="promptContentInput" style="margin-top: 8px">Content</label>
            <textarea id="promptContentInput" class="textarea" rows="14" bind:value={editingPromptContent}></textarea>

            <div style="display:flex; gap:8px; margin-top:8px">
              <button class="btn primary" on:click={savePrompt}>Save</button>
            </div>
          </div>
        {:else}
          <div class="muted">Select a prompt to edit.</div>
        {/if}
      </div>
    </div>
  </div>
{/if}

{#if showReprocess}
  <div
    class="modalBackdrop"
    role="button"
    tabindex="0"
    on:keydown={closeReprocessOnKeydown}
    on:click|self={() => (showReprocess = false)}
  >
    <div class="modal" role="dialog" aria-modal="true" aria-label="Re-process options">
      <div class="modalHeader">
        <div class="h2">Re-process</div>
        <button class="btn" on:click={() => (showReprocess = false)}>Close</button>
      </div>
      <div class="modalBody" style="grid-template-columns: 1fr">
        <div class="muted">
          This will re-run LLM steps using the existing transcript (no re-transcription).
        </div>

        <div class="row" style="margin-top: 8px; flex-wrap: wrap">
          <label class="check">
            <input type="checkbox" bind:checked={reprocessSummarize} />
            Re-summarize
          </label>
          <label class="check">
            <input type="checkbox" bind:checked={reprocessActionItems} />
            Re-create action items
          </label>
        </div>

        <div style="display:flex; gap:8px; margin-top:10px">
          <button class="btn primary" disabled={reprocessBusy || (!reprocessSummarize && !reprocessActionItems)} on:click={submitReprocess}>
            {reprocessBusy ? 'Queueing…' : 'Queue re-process'}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if showTags}
  <div
    class="modalBackdrop"
    role="button"
    tabindex="0"
    on:keydown={closeTagsOnKeydown}
    on:click|self={() => (showTags = false)}
  >
    <div class="modal" role="dialog" aria-modal="true" aria-label="Edit tags">
      <div class="modalHeader">
        <div class="h2">Tags</div>
        <button class="btn" on:click={() => (showTags = false)}>Close</button>
      </div>
      <div class="modalBody" style="grid-template-columns: 1fr">
        <div class="muted">Comma-separated tags. Stored in the database and searchable.</div>

        <label class="label" for="tagsInputField" style="margin-top: 8px">Tags</label>
        <input
          id="tagsInputField"
          class="input"
          bind:value={tagsInput}
          placeholder="e.g. meeting, finance, urgent"
        />

        <div style="display:flex; gap:8px; margin-top:10px">
          <button class="btn primary" disabled={tagsBusy} on:click={saveTags}>
            {tagsBusy ? 'Saving…' : 'Save tags'}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .layout {
    display: grid;
    grid-template-columns: 360px 1fr;
    height: 100vh;
  }
  .sidebar {
    border-right: 1px solid var(--border);
    background: var(--panel2);
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .sidebarHeader {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px;
    border-bottom: 1px solid var(--border);
  }
  .sidebarHeaderLeft { display: flex; align-items: center; gap: 10px; min-width: 0; }
  .title { font-weight: 700; }
  .queuePill {
    font-size: 0.8rem;
    color: var(--muted);
    border: 1px solid var(--border);
    background: rgba(148,163,184,0.08);
    padding: 4px 8px;
    border-radius: 999px;
    white-space: nowrap;
  }
  .uploadForm {
    padding: 12px;
    display: grid;
    gap: 8px;
    border-bottom: 1px solid var(--border);
  }
  .label { font-size: 0.85rem; color: var(--muted); }
  .row { display: flex; gap: 10px; }
  .check { display: flex; gap: 8px; align-items: center; color: var(--text); font-size: 0.9rem; }
  .list { padding: 12px; overflow: auto; flex: 1; min-height: 0; }
  .listHeaderRow { display: grid; gap: 8px; margin-bottom: 8px; }
  .input.search { padding: 0.45rem 0.6rem; border-radius: 10px; }
  .listHeader { font-size: 0.85rem; color: var(--muted); margin-bottom: 8px; }
  .item {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px;
    padding: 8px;
    border-radius: 10px;
    border: 1px solid transparent;
    margin-bottom: 8px;
  }
  .item.active { border-color: rgba(16,185,129,0.6); background: rgba(16,185,129,0.06); }
  .itemMain {
    text-align: left;
    border: 0;
    background: transparent;
    color: inherit;
    cursor: pointer;
    padding: 0;
  }
  .itemName { font-weight: 600; }
  .itemMeta { font-size: 0.8rem; }
  .tagRow { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
  .tag {
    font-size: 0.75rem;
    color: var(--muted);
    border: 1px solid rgba(148,163,184,0.22);
    background: rgba(148,163,184,0.08);
    padding: 2px 6px;
    border-radius: 999px;
  }
  .main { padding: 18px; overflow: auto; }
  .jobBar {
    position: sticky;
    top: 0;
    z-index: 5;
    border: 1px solid var(--border);
    background: rgba(15,23,42,0.92);
    backdrop-filter: blur(10px);
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 12px;
    display: grid;
    gap: 6px;
  }
  .jobTop { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }
  .progress { height: 10px; border-radius: 999px; background: rgba(148,163,184,0.15); overflow: hidden; }
  .progressFill { height: 100%; background: var(--accent); }
  .progressFill.indeterminate {
    background: linear-gradient(90deg, rgba(16,185,129,0.15), var(--accent), rgba(16,185,129,0.15));
    animation: progress-indeterminate 1.2s ease-in-out infinite;
  }
  @keyframes progress-indeterminate {
    0% { transform: translateX(-120%); }
    100% { transform: translateX(320%); }
  }
  @media (prefers-reduced-motion: reduce) {
    .progressFill.indeterminate { animation: none; }
  }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .headerActions { display: flex; gap: 8px; }
  .h1 { font-size: 1.3rem; font-weight: 800; }
  .panel { border: 1px solid var(--border); background: rgba(17,24,39,0.5); padding: 12px; border-radius: 12px; margin-bottom: 12px; }
  .panelTitle { font-weight: 700; margin-bottom: 8px; }
  .grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 12px; }
  .segments { display: grid; gap: 10px; max-height: 55vh; overflow: auto; padding-right: 8px; }
  .seg { padding: 10px; border: 1px solid var(--border); border-radius: 10px; background: rgba(15,23,42,0.35); }
  .segMeta { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size: 0.8rem; margin-bottom: 4px; }
  .pre { white-space: pre-wrap; margin: 0; }
  .markdown { line-height: 1.55; }
  .markdown :global(p) { margin: 0 0 0.75rem 0; }
  .markdown :global(p:last-child) { margin-bottom: 0; }
  .markdown :global(h1),
  .markdown :global(h2),
  .markdown :global(h3) { margin: 0.75rem 0 0.5rem; line-height: 1.25; }
  .markdown :global(h1) { font-size: 1.15rem; }
  .markdown :global(h2) { font-size: 1.05rem; }
  .markdown :global(h3) { font-size: 1.0rem; }
  .markdown :global(ul),
  .markdown :global(ol) { margin: 0.25rem 0 0.75rem; padding-left: 1.2rem; }
  .markdown :global(li) { margin: 0.2rem 0; }
  .markdown :global(a) { color: var(--accent); text-decoration: none; }
  .markdown :global(a:hover) { text-decoration: underline; }
  .markdown :global(code) {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
    font-size: 0.9em;
    background: rgba(148,163,184,0.14);
    border: 1px solid rgba(148,163,184,0.22);
    padding: 0.05rem 0.25rem;
    border-radius: 8px;
  }
  .markdown :global(pre) {
    overflow: auto;
    padding: 10px;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: rgba(15,23,42,0.35);
  }
  .markdown :global(pre code) { background: transparent; border: 0; padding: 0; }
  .markdown :global(blockquote) {
    margin: 0.5rem 0;
    padding: 0.25rem 0.75rem;
    border-left: 3px solid rgba(148,163,184,0.35);
    color: var(--muted);
  }
  .tableWrap { overflow: auto; }
  .aiTable {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  .aiTable th,
  .aiTable td {
    padding: 8px 10px;
    border-bottom: 1px solid rgba(148,163,184,0.18);
    vertical-align: top;
    text-align: left;
    white-space: pre-wrap;
  }
  .aiTable th {
    position: sticky;
    top: 0;
    background: rgba(15,23,42,0.92);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid rgba(148,163,184,0.28);
    font-weight: 800;
    color: var(--text);
    z-index: 1;
  }
  .aiTable tr:hover td { background: rgba(148,163,184,0.06); }
  .empty { padding: 80px 24px; }
  .error { color: #fecaca; background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.4); padding: 8px; border-radius: 10px; }
  .modalBackdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: grid; place-items: center; padding: 16px; }
  .modal { width: min(980px, 96vw); background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 12px; }
  .modalHeader { display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid var(--border); }
  .h2 { font-size: 1.1rem; font-weight: 800; }
  .modalBody { display: grid; grid-template-columns: 280px 1fr; gap: 12px; padding: 12px; }
  .promptList { display: grid; gap: 8px; align-content: start; }
  .promptItem { text-align: left; border: 1px solid var(--border); border-radius: 10px; background: rgba(15,23,42,0.35); color: var(--text); padding: 10px; cursor: pointer; }
  .promptEditor { display: grid; gap: 8px; }

  @media (max-width: 900px) {
    .layout { grid-template-columns: 1fr; }
    .grid { grid-template-columns: 1fr; }
  }
</style>

