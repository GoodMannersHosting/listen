<script>
  import { onMount } from 'svelte';
  import Sidebar from './components/Sidebar.svelte';
  import UploadArea from './components/UploadArea.svelte';
  import ConversationView from './components/ConversationView.svelte';
  import { profiles, currentProfile, conversations, currentConversation } from './stores';
  import { api } from './api';

  let showUploadArea = true;

  onMount(async () => {
    await loadProfiles();
    loadActiveProfileFromStorage();
  });

  async function loadProfiles() {
    try {
      const profileList = await api.get('/profiles');
      profiles.set(profileList || []);
    } catch (error) {
      console.error('Failed to load profiles:', error);
    }
  }

  function loadActiveProfileFromStorage() {
    const stored = localStorage.getItem('activeProfileId');
    if (stored) {
      profiles.subscribe(profileList => {
        const profile = profileList.find(p => p.id === parseInt(stored));
        if (profile) {
          currentProfile.set(profile);
        } else if (profileList.length > 0) {
          currentProfile.set(profileList[0]);
        }
      })();
    } else {
      profiles.subscribe(profileList => {
        if (profileList.length > 0) {
          currentProfile.set(profileList[0]);
        }
      })();
    }
  }

  function handleShowUpload() {
    showUploadArea = true;
    currentConversation.set(null);
  }

  function handleConversationReady({ conversationId }) {
    loadConversation(conversationId);
  }

  async function loadConversation(conversationId) {
    try {
      const conversation = await api.get(`/conversations/${conversationId}`);
      currentConversation.set(conversation);
      showUploadArea = false;
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  }

  $: if (showUploadArea) {
    currentConversation.set(null);
  } else if ($currentConversation) {
    showUploadArea = false;
  }

  // Handle window messages for conversation loading
  onMount(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('message', (event) => {
        const detail = event.detail;
        if (detail?.type === 'loadConversation') {
          loadConversation(detail.conversationId);
        } else if (detail?.type === 'showUpload') {
          handleShowUpload();
        }
      });
    }
  });
</script>

<div class="app-container">
  <Sidebar on:showUpload={handleShowUpload} />
  <main class="main-content">
    {#if showUploadArea}
      <UploadArea on:conversationReady={handleConversationReady} />
    {:else if $currentConversation}
      <ConversationView />
    {:else}
      <UploadArea on:conversationReady={handleConversationReady} />
    {/if}
  </main>
</div>

<style>
  .app-container {
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: var(--main-bg);
    overflow: hidden;
    min-height: 0;
  }
</style>
