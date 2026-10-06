---
name: brag
description: Create accurate project-specific launch stories, media plans, and optional rendered video.
version: 1.0.0
tags: [engineering, openoperator]
---

# brag

## Classification

- **Agent Zero capability:** workflow/instruction skill and external-rendering adapter.
- **Native outputs:** evidence-based storyboard, demo script, poster plan, release summary, and share copy.
- **Optional dependencies:** Node.js 22+, FFmpeg, Hyperframes, and any separately installed `latent-spaces/brag` rendering tools.

Adapted from `latent-spaces/brag` (MIT); its rendering runtime is not vendored into Agent Zero. Only after production verification: inspect the real project and UI, plan a specific 15-25 second storyboard, compose, validate, optionally render video or a poster, and write share copy. Exclude secrets, tokens, internal URLs, customer data, and invented claims.

Detect rendering dependencies lazily on invocation; never install at startup or import them during normal Agent Zero startup. Missing Node.js, FFmpeg, Hyperframes, or upstream Brag tools blocks rendering only: still return the native textual outputs with explicit `NOT RENDERED` evidence.
