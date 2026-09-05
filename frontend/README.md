# Mpostele frontend

This folder contains the current frontend prototype for the mpostele project: a Vite + Vue interface for planning and previewing social content workflows.

## What this prototype includes

- a content calendar dashboard
- channel and campaign summary metrics
- a draft queue with scheduling data
- a theme toggle and design system styling
- a dark/light UI treatment based on a shared token palette

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
