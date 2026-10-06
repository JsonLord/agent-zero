# Tiny Coder Profile DOX

## Purpose

- Own the bundled tiny-coder specialist profile.

## Ownership

- agent.yaml owns discovery metadata; prompts/ owns behavior.

## Local Contracts

- Preserve the bounded role, evidence requirements, delegation boundaries, and goal checkpoint discipline.
- Do not store secrets or runtime state here.
- Without overrides, Tiny Coder inherits the ordinary scoped model preset. Operators may bind it to a small backend with `TINY_CODER_PROVIDER`, `TINY_CODER_MODEL`, optional `TINY_CODER_API_BASE`, and optional `TINY_CODER_API_KEY`; startup stores only a secret-free profile preset and keeps the key in the normal provider-key store.

## Work Guidance

- Keep instructions concise and native-profile compatible.

## Verification

- Run specialist discovery and delegation tests.

## Child DOX Index

No child DOX files.
