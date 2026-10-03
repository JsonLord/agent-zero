---
name: paperclip-board-manager
description: Read and manage Paperclip companies/projects/issues through the configured Paperclip HTTP API. Use for board/project/task coordination in the Paperclip instance.
tags:
  - paperclip
  - board
  - project-management
allowed-tools:
  - code_execution_tool
---

# Paperclip board manager

Use `scripts/paperclip_api.py` from this skill directory. It only accepts HTTPS `PAPERCLIP_BASE_URL` values and `/api/*` paths. Authentication is optional via the `PAPERCLIP_API_TOKEN` environment secret; never print that token.

The configured starter base URL is `https://leon4gr45-paperclip-founder.hf.space`.

Useful routes confirmed in the Paperclip branch:
- `GET /api/companies/{companyId}/issues` — list/filter company issues.
- `GET /api/issues/{issueId}` — fetch one issue; identifiers such as `PAP-39` are accepted by the server.
- `GET /api/companies/{companyId}/projects` — list company projects.
- `POST /api/companies/{companyId}/projects` — create a project.
- `GET /api/projects/{projectId}` and `PATCH /api/projects/{projectId}` — read/update a project.
- `GET /api/companies/{companyId}/labels` and `POST /api/companies/{companyId}/labels` — list/create issue labels.

Examples:

```bash
python agents/spynel/skills/paperclip-board-manager/scripts/paperclip_api.py GET /api/companies/COMPANY_ID/issues
python agents/spynel/skills/paperclip-board-manager/scripts/paperclip_api.py GET /api/companies/COMPANY_ID/projects
python agents/spynel/skills/paperclip-board-manager/scripts/paperclip_api.py PATCH /api/projects/PROJECT_ID --json '{"name":"Updated name"}'
```

For mutations, inspect the live response/schema or the matching Paperclip route before inventing fields. Treat 401/403 as an authentication/authorization problem rather than retrying blindly. Return the API error body to the user with secrets redacted.
