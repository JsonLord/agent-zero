---
name: git-worktree
description: Isolate parallel write-capable tasks with Git worktrees and branches.
version: 1.0.0
tags: [engineering, openoperator]
---

# git-worktree

Use read-only concurrency when possible. Before parallel writers, assign separate branches/worktrees and an explicit merge owner. Verify clean state, base SHA and conflicting paths. Never delete an unmerged worktree without approval.
