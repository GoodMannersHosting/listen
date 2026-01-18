# Svelte Frontend for Listen

This is the Svelte frontend for the Audio Transcription Tool. It replaces the vanilla JS frontend with a modern, reactive component-based architecture that fixes scrolling and sizing issues.

## Setup

1. Install dependencies:
```bash
cd frontend
yarn install
```

2. Build for production:
```bash
yarn build
```

This will output the built files to `../static/` directory.

3. For development with hot reload:
```bash
yarn dev
```

This starts a dev server on port 5173 with proxy to the FastAPI backend on port 8000.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Sidebar.svelte
│   │   ├── UploadArea.svelte
│   │   ├── ConversationView.svelte
│   │   ├── TranscriptTab.svelte
│   │   ├── SummaryTab.svelte
│   │   ├── ActionItemsTab.svelte
│   │   ├── AudioPlayer.svelte
│   │   ├── ProfileModal.svelte
│   │   └── RenameModal.svelte
│   ├── stores.js          # Svelte stores for state management
│   ├── api.js             # API client
│   ├── utils.js           # Utility functions
│   ├── App.svelte         # Main app component
│   ├── app.css            # Global styles
│   └── main.js            # Entry point
├── package.json
└── vite.config.js

```

## Key Features

- **Proper Scrolling**: All scrollable content areas use proper flexbox constraints with `flex: 1`, `min-height: 0`, and `overflow-y: auto` to ensure content scrolls correctly within the viewport.

- **Reactive State**: Uses Svelte stores for centralized state management.

- **Component-based**: Clean separation of concerns with reusable components.

- **Type-safe**: Uses Svelte's reactive syntax for type-safe reactive updates.

## Scrolling Fix

The key fix for scrolling is in the CSS for `.tab-content`, `.transcript-content`, `.summary-content`, and `.action-items-content`:

```css
.tab-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.transcript-content,
.summary-content,
.action-items-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
```

This ensures that:
1. Parent containers constrain height with `overflow: hidden` and `min-height: 0`
2. Content areas fill available space with `flex: 1`
3. Content scrolls when it overflows with `overflow-y: auto`
