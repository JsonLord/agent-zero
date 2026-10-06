---
name: playwright
description: Run browser journeys, accessibility checks, and theme/responsive validation.
version: 1.0.0
tags: [engineering, openoperator]
---

# playwright

## Classification

- **Agent Zero capability:** workflow/instruction skill and external-tool adapter.
- **Not bundled:** a Playwright browser/runtime or a skill-local executable.
- **Optional dependency:** a separately available Playwright installation and its browser binaries.

Discover the actual application URL. When Playwright is available, exercise real controls, console and network failures, keyboard flow, dark/light themes, hover/active/disabled states, and responsive viewports. Capture screenshots for visible changes and redact secrets. Detect the tool lazily when browser verification is requested; missing Playwright or browser binaries must not affect Agent Zero startup and must be reported as `NOT EXECUTED`, not as a passing browser check.
