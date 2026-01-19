<script>
  import { createEventDispatcher } from 'svelte';
  import { profiles, currentProfile } from '../stores';
  import { api } from '../api';

  const dispatch = createEventDispatcher();

  let name = '';
  let displayName = '';

  async function createProfile() {
    if (!name.trim()) {
      alert('Profile name is required');
      return;
    }

    try {
      const newProfile = await api.post('/profiles', {
        name: name.trim(),
        display_name: displayName.trim() || null
      });

      const profileList = await api.get('/profiles');
      profiles.set(profileList || []);

      currentProfile.set(newProfile);
      dispatch('close');
      name = '';
      displayName = '';
    } catch (error) {
      alert(error.message || 'Failed to create profile');
    }
  }

  function handleClose() {
    name = '';
    displayName = '';
    dispatch('close');
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      handleClose();
    }
  }
</script>

<div class="modal" on:click|self={handleClose} on:keydown={handleKeydown}>
  <div class="modal-content" on:click|stopPropagation>
    <h3>Create New Profile</h3>
    <input type="text" placeholder="Profile Name" required bind:value={name} />
    <input type="text" placeholder="Display Name (optional)" bind:value={displayName} />
    <div class="modal-actions">
      <button class="btn-primary" on:click={createProfile}>Create</button>
      <button class="btn-secondary" on:click={handleClose}>Cancel</button>
    </div>
  </div>
</div>

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
