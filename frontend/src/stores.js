import { writable } from 'svelte/store';

export const currentProfile = writable(null);
export const profiles = writable([]);
export const conversations = writable([]);
export const currentConversation = writable(null);
export const transcriptSegments = writable(null);
export const sidebarCollapsed = writable(false);
