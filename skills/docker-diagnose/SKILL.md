---
name: docker-diagnose
description: Diagnose container runtime, privilege, filesystem and startup behavior.
version: 1.0.0
tags: [engineering, openoperator]
---

# docker-diagnose

Separate container detection from capabilities. Record image, command, UID/GID, mounts, writable paths, executable availability, health and logs without secrets. Do not add root, sudo, setuid, capabilities, SSH, or password hacks to bypass least privilege.
