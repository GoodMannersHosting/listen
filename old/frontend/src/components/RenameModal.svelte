<script>
  import { createEventDispatcher } from 'svelte';
  import { conversations, currentProfile, currentConversation } from '../stores';
  import { api } from '../api';

  const dispatch = createEventDispatcher();

  export let conversationId;

  let title = '';

  $: conversation = $conversations.find(c => c.id === conversationId);
  $: if (conversation) {
    title = conversation.title || `Conversation ${conversationId}`;
  }

  async function renameConversation() {
    if (!title.trim()) {
      alert('Title cannot be empty');
      return;
    }

    try {
      await api.put(`/conversations/${conversationId}`, { title: title.trim() });
      const convList = await api.get(`/conversations?profile_id=${$currentProfile.id}`);
      conversations.set(convList || []);
      currentConversation.update((cc) => {
        if (cc?.id === conversationId) {
          return { ...cc, title: title.trim() };
        }
        return cc;
      });
      dispatch('close');
    } catch (error) {
      alert(error.message || 'Failed to rename conversation');
    }
  }

  function handleClose() {
    dispatch('close');
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      renameConversation();
    } else if (e.key === 'Escape') {
      handleClose();
    }
  }
</script>

{#if conversationId}
  <div class="modal" on:click|self={handleClose} on:keydown={handleKeydown}>
    <div class="modal-content" on:click|stopPropagation>
      <h3>Rename Conversation</h3>
      <input type="text" placeholder="Conversation title" required bind:value={title} />
      <div class="modal-actions">
        <button class="btn-primary" on:click={renameConversation}>Save</button>
        <button class="btn-secondary" on:click={handleClose}>Cancel</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background-color: var(--sidebar-bg);
    padding: 2rem;
    border-radius: 8px;
    max-width: 400px;
    width: 90%;
  }

  .modal-content h3 {
    margin-bottom: 1rem;
  }

  .modal-content input {
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 1rem;
    background-color: var(--hover-bg);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
  }

  .modal-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .modal-actions button {
    width: auto;
    margin: 0;
  }
</style>
