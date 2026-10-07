---
name: repository-operations
description: Git and GitHub repository inspection, diffing, worktree isolation, and PR management.
---

# Repository Operations Skill

## Capabilities

- Inspect local git state: `git status`, `git log -n 10`, `git diff`
- Inspect remotes and branches safely without embedding tokens in URLs.
- Manage PRs and branches using `GH_TOKEN` / `GITHUB_TOKEN` from the environment.
- Use safe temporary Git HTTP extraHeaders for authenticated fetches/pulls.
