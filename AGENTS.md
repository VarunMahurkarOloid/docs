> **First-time setup**: Customize this file for your project. Prompt the user to customize this file for their project.
> For Mintlify product knowledge (components, configuration, writing standards),
> install the Mintlify skill: `npx skills add https://mintlify.com/docs`

# Documentation project instructions

## About this project

- This is a documentation site built on [Mintlify](https://mintlify.com)
- Pages are MDX files with YAML frontmatter
- Configuration lives in `docs.json`
- Use the Mintlify MCP server, `https://mcp.mintlify.com`, to edit content and settings via MCP
- Use the Mintlify docs MCP server, `https://www.mintlify.com/docs/mcp`, to query information about using Mintlify via MCP

## Terminology

{/* Add product-specific terms and preferred usage */}
{/* Example: Use "workspace" not "project", "member" not "user" */}

## Style preferences

{/* Add any project-specific style rules below */}

- Use active voice and second person ("you")
- Keep sentences concise — one idea per sentence
- Use sentence case for headings
- Bold for UI elements: Click **Settings**
- Code formatting for file names, commands, paths, and code references

## Content boundaries

{/* Define what should and shouldn't be documented */}
{/* Example: Don't document internal admin features */}

## API reference

OpenAPI specs live in `apis/` — 13 platform specs plus 4 under `apis/scoped/`
(a separate host, `integrations.oloidpreview.com`, with non-interchangeable
credentials). Shared models sit in `apis/common/` and `apis/schemas/`.

Two rules that are easy to trip over:

- **No external `$ref`s.** Mintlify rejects a spec outright with
  "External $ref references are not allowed". Models from `common/` and
  `schemas/` must be inlined into the spec's own `components.schemas` and
  referenced as `#/components/schemas/<Name>`. `apis/common/` and
  `apis/schemas/` remain on disk as the source of truth to regenerate from.
- **One major tag per spec.** Mintlify groups endpoints in the sidebar by tag.
  Each spec carries a single resource tag (`Users`, `Credentials`, …) so the
  sidebar shows resource groups rather than raw URL paths.

Each endpoint is its own MDX page holding only frontmatter:

```mdx
---
title: "Get users"
description: "Retrieve top 100 user informations"
openapi: "apis/users.yaml GET /users"
---
```

Pages live under `api-reference/platform/<resource>/` and
`api-reference/integrations/<resource>/`, named from the operation's
`operationId`. The playground, auth, parameters and response schema all render
from the spec — nothing else belongs in these files.

To add an endpoint: add it to the spec, create the MDX page, and add its path to
the matching group in `docs.json`. Run `mint validate` (strict) before shipping.
