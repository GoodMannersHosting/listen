<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { profiles, currentProfile, conversations, sidebarCollapsed, currentConversation } from '../stores';
  import { api } from '../api';
  import { formatDate } from '../utils';
  import ProfileModal from './ProfileModal.svelte';
  import RenameModal from './RenameModal.svelte';

  const dispatch = createEventDispatcher();

  let showProfileModal = false;
  let showRenameModal = false;
  let renameConversationId = null;

  $: activeProfileId = $currentProfile?.id;

  $: if ($currentProfile) {
    loadConversations($currentProfile.id);
  }

  // Listen for refresh events from upload completion
  onMount(() => {
    const handleRefresh = () => {
      if ($currentProfile) {
        loadConversations($currentProfile.id);
      }
    };
    window.addEventListener('refreshConversations', handleRefresh);
    return () => {
      window.removeEventListener('refreshConversations', handleRefresh);
    };
  });

  function toggleSidebar() {
    sidebarCollapsed.update(c => !c);
  }

  async function handleProfileChange(e) {
    const profileId = parseInt(e.target.value);
    if (profileId) {
      const profile = $profiles.find(p => p.id === profileId);
      if (profile) {
        currentProfile.set(profile);
        localStorage.setItem('activeProfileId', profileId.toString());
      }
    }
  }

  async function loadConversations(profileId) {
    try {
      const convList = await api.get(`/conversations?profile_id=${profileId}`);
      conversations.set(convList || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }

  function handleNewConversation() {
    dispatch('showUpload');
  }

  async function handleConversationClick(conversationId) {
    try {
      const conversation = await api.get(`/conversations/${conversationId}`);
      currentConversation.set(conversation);
      window.dispatchEvent(new CustomEvent('message', {
        detail: { type: 'loadConversation', conversationId }
      }));
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  }

  function handleRename(conversationId) {
    renameConversationId = conversationId;
    showRenameModal = true;
  }

  function handleDelete(conversationId) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    api.delete(`/conversations/${conversationId}`).then(() => {
      loadConversations($currentProfile?.id);
    });
  }

</script>

<aside class="sidebar" class:collapsed={$sidebarCollapsed}>
  <div class="sidebar-header">
    <h2>Transcribe</h2>
    <button class="sidebar-toggle" on:click={toggleSidebar} aria-label="Toggle sidebar">☰</button>
  </div>

  <div class="profile-section">
    <select class="profile-select" value={$currentProfile?.id} on:change={handleProfileChange}>
      <option value="">Select Profile...</option>
      {#each $profiles as profile}
        <option value={profile.id}>{profile.display_name || profile.name}</option>
      {/each}
    </select>
    <button class="btn-secondary" on:click={() => showProfileModal = true}>+ New Profile</button>
  </div>

  <div class="sidebar-content">
    <button class="btn-primary" on:click={handleNewConversation}>+ New Conversation</button>
    <div class="conversations-list">
      {#each $conversations as conversation}
        <div class="conversation-item">
          <div class="conversation-info" on:click={() => handleConversationClick(conversation.id)}>
            <div class="conversation-title">{conversation.title || `Conversation ${conversation.id}`}</div>
            <div class="conversation-time">{formatDate(conversation.created_at)}</div>
          </div>
          <div class="conversation-actions">
            <button class="conversation-action-btn" on:click|stopPropagation={() => handleRename(conversation.id)} title="Rename">✏️</button>
            <button class="conversation-action-btn delete" on:click|stopPropagation={() => handleDelete(conversation.id)} title="Delete">🗑️</button>
          </div>
        </div>
      {/each}
    </div>
  </div>
</aside>

{#if showProfileModal}
  <ProfileModal on:close={() => showProfileModal = false} />
{/if}

{#if showRenameModal}
  <RenameModal conversationId={renameConversationId} on:close={() => { showRenameModal = false; renameConversationId = null; }} />
{/if}

<style>
  .sidebar {
    width: var(--sidebar-width);
    background-color: var(--sidebar-bg);
    display: flex;
    flex-direction: column;
    transition: width 0.3s ease;
    border-right: 1px solid var(--border-color);
  }

  .sidebar.collapsed {
    width: var(--sidebar-collapsed-width);
  }

  .sidebar.collapsed .sidebar-content,
  .sidebar.collapsed .profile-section {
    display: none;
  }

  .sidebar.collapsed .sidebar-header h2 {
    display: none;
  }

  .sidebar.collapsed .sidebar-header {
    justify-content: center;
    padding: 1rem 0.5rem;
  }

  .sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
  }

  .sidebar-header h2 {
    font-size: 1.25rem;
    font-weight: 600;
  }

  .sidebar-toggle {
    background: none;
    border: none;
    color: var(--text-primary);
    cursor: pointer;
    font-size: 1.5rem;
    padding: 0.5rem;
  }

  .profile-section {
    padding: 1rem;
    border-bottom: 1px solid var(--border-color);
  }

  .profile-select {
    width: 100%;
    padding: 0.5rem;
    background-color: var(--hover-bg);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    margin-bottom: 0.5rem;
  }

  .btn-primary, .btn-secondary {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: background-color 0.2s;
    width: 100%;
    margin-top: 0.5rem;
  }

  .btn-primary {
    background-color: var(--button-primary);
    color: white;
  }

  .btn-primary:hover {
    background-color: var(--button-primary-hover);
  }

  .btn-secondary {
    background-color: var(--button-secondary);
    color: var(--text-primary);
  }

  .btn-secondary:hover {
    background-color: var(--button-secondary-hover);
  }

  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
  }

  .conversations-list {
    margin-top: 1rem;
  }

  .conversation-item {
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .conversation-item:hover {
    background-color: var(--hover-bg);
  }

  .conversation-item:hover .conversation-actions {
    opacity: 1;
  }

  .conversation-info {
    flex: 1;
    min-width: 0;
  }

  .conversation-title {
    font-size: 0.9rem;
    font-weight: 500;
    margin-bottom: 0.25rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .conversation-time {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .conversation-actions {
    display: flex;
    gap: 0.25rem;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .conversation-action-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    font-size: 0.85rem;
    border-radius: 3px;
    transition: all 0.2s;
  }

  .conversation-action-btn:hover {
    background-color: var(--hover-bg);
    color: var(--text-primary);
  }

  .conversation-action-btn.delete:hover {
    color: #ff6b6b;
  }
</style>
