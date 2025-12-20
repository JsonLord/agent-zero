---
name: scientific-schematics
description: "Core skill for creating scientific schematics and diagrams. Use this skill to generate high-quality, publication-ready schematics based on user descriptions."
allowed-tools: [Bash]
---

# Scientific Schematics

## Overview

This skill is designed to provide comprehensive support for creating scientific schematics and diagrams. It enables the agent to generate high-quality, publication-ready schematics based on user descriptions.

## When to Use This Skill

This skill should be used when:
- A user requests a scientific schematic or diagram.
- A visualization is needed to explain a complex concept.
- A diagram is required for a scientific publication.

## Core Workflow

1.  **Understand the user's request:**
    *   Carefully read the user's description of the desired schematic.
    *   Ask clarifying questions if the description is ambiguous.

2.  **Generate the schematic:**
    *   Use the `generate_schematic.py` script to create the schematic.
    *   The script takes a description of the schematic as input and generates an image file as output.
    ```bash
    python scripts/generate_schematic.py "your diagram description" -o figures/output.png
    ```

3.  **Provide the schematic to the user:**
    *   Once the schematic has been generated, provide the image file to the user.
