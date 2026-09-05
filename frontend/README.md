# Mpostele frontend

This folder contains the current frontend prototype for the mpostele project: a Vite + Vue interface for planning and previewing social content workflows.

## What this prototype includes

- a content calendar dashboard
- channel and campaign summary metrics
- a draft queue with scheduling data
- a theme toggle and design system styling
- a dark/light UI treatment based on a shared token palette
- a capture command builder that validates the platform URL and output folder, and masks the password by default (with an explicit "show password" toggle) so it isn't exposed on screen by default
- a theme-aware favicon that follows the OS color scheme by default and switches instantly when the in-app theme toggle is used

## Data persistence

Settings (theme choice, platform URL, username, target path, output folder) persist locally across reloads using [sql.js](https://github.com/sql-js/sql.js) — SQLite compiled to WebAssembly, running entirely client-side. The exported database file is stored as raw bytes in the browser's IndexedDB, so no server or cloud service is involved and the app stays fully offline.

The password field is intentionally **never persisted**: it's excluded from the stored JSON and starts empty on every reload. This avoids writing a plaintext credential to disk-backed browser storage.

See [src/db/sqlite.js](src/db/sqlite.js) for the persistence module (a small `settings(key, value)` table) and the `onMounted`/`watch` wiring in [src/App.vue](src/App.vue) for how fields are loaded and saved.

## Why it exists

This UI is a design and interaction prototype for the broader mpostele concept. It demonstrates the planning experience for short-form product content while the underlying capture, motion, and compositing pipeline is still being built.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

## Verify the production build

```bash
cd frontend
npm run build
```

## Current status

This frontend is a working prototype, not the final end-to-end video automation stack. The long-term pipeline still needs the actual browser capture, motion generation, FFmpeg composition, and export logic described in the project docs.
