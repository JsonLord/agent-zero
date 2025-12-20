---
name: research-lookup
description: "Core skill for performing research lookups. Use this skill to find and synthesize information from a variety of sources."
allowed-tools: [search_engine]
---

# Research Lookup

## Overview

This skill is designed to provide comprehensive support for performing research lookups. It enables the agent to find and synthesize information from a variety of sources.

## When to Use This Skill

This skill should be used when:
- A user asks a question that requires external knowledge.
- A user requests a summary of a topic.
- A user asks for citations for a claim.

## Core Workflow

1.  **Understand the user's request:**
    *   Carefully read the user's question or request.
    *   Identify the key terms and concepts.

2.  **Perform a search:**
    *   Use the `search_engine` tool to search for relevant information.
    *   Use a variety of search terms to ensure comprehensive coverage.

3.  **Synthesize the findings:**
    *   Read through the search results and identify the most relevant information.
    *   Synthesize the information into a concise summary.
    *   Include citations for all claims.

4.  **Provide the summary to the user:**
    *   Present the summary to the user in a clear and easy-to-understand format.
