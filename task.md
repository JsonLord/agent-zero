# Project: SWE Developer Agent Implementation

## 1. Project Overview

This project aims to enhance the `agent-0` repository by implementing a sophisticated Software Engineering (SWE) Developer Agent. This new agent will have a comprehensive set of capabilities for software development, including planning, research, coding, deployment, and task management. It will leverage a multi-agent architecture and integrate several external tools to achieve its goals.

## 2. Developer Agent Profile (`developer-agent`)

### 2.1. New System Prompt

The existing system prompt for the `developer-agent` will be replaced with the following:

> Coding Planner. Utilise subagents to achieve tasks. Write files yourself using write_file() function. if more than 2 files need to be edited to achieve something, utilise the Plan prompt.
> Main subagents are
> git-agent
> huggingface
> jules-agent
> monitor-agent
> taskmaster agent

### 2.2. Core Responsibilities

*   Orchestrate sub-agents to accomplish complex development tasks.
*   Manage the entire development lifecycle from ideation to deployment.
*   Interact with the user for clarification and decision-making.
*   Maintain project state and documentation.

## 3. Sub-agent Integration

The developer agent will delegate tasks to the following specialized sub-agents:

*   **`git-agent`:** For managing git repositories and making simple, single-file changes.
*   **`huggingface-agent`:** For all Hugging Face related tasks, including Space creation, deployment, and management.
*   **`jules-agent`:** For complex coding tasks, working on specific components, and making changes to project files on GitHub.
*   **`monitor-agent`:** For retrieving logs from Hugging Face Spaces and Jules.
*   **`research-agent`:** For conducting research on external tools, libraries, and solutions.
*   **`taskmaster-agent`:** For managing tasks, based on `todo.ai`.
*   **`task_manager_subagent`:** An asynchronous agent for monitoring and executing tasks.

## 4. Core Workflows

The developer agent will trigger specific workflows based on user keywords.

### 4.1. `Develop` Workflow

1.  **Ideation Session:**
    *   Initiate a logged ideation session (`/app/ideate/{project_name}_ideate_session_{number}`).
    *   Involve the `research-agent` to investigate git directories, find solutions, and reflect on ideas.
2.  **Automated Analysis:**
    *   Upload the ideation log to `JsonLord/agent-notes/logs` on GitHub.
    *   Analyze the log to identify components, questions, and potential external services.
    *   Use the `research-agent` to find relevant Hugging Face Spaces or GitHub projects.
    *   `git-agent` and `huggingface-agent` will analyze and recommend integration strategies.
3.  **User Interaction & Planning:**
    *   Wait for user feedback on the recommendations.
    *   Integrate `mermaid-js` to create and upload diagrams of the proposed architecture to GitHub.
4.  **QA Session:**
    *   Present a question sheet to the user for clarification.
    *   Reflect on the answers and update the project plan. Repeat up to 3 times if necessary.
5.  **Task Generation:**
    *   Implement `fxstein/todo.ai` as a task manager.
    *   Create tasks based on the refined plan, categorized into: `Deploy`, `Plan`, `Research`, `Build-in-steps`, `API-Endpoints`, `Build`, `Last features`.
    *   Define a test goal for each task.
    *   Assign agents to each task and test.
    *   Tag tasks as `sequential` or `parallel` with dependency information.

### 4.2. `Deploy` Workflow

1.  **Space Creation:**
    *   Use `huggingface-agent` to create a new Hugging Face Space.
2.  **Deployment Strategy:**
    *   For GitHub repos, investigate with `git-agent` and create a `Dockerfile` with `git clone`.
    *   For custom projects, use the `Plan` workflow to decide between writing files directly or using `jules-agent`.
3.  **Deployment and Monitoring:**
    *   Upload files to the Space using `huggingface-agent`.
    *   Wait 5 minutes, then use `monitor-agent` to retrieve logs.
    *   Debug and fix any issues until the Space is running.
4.  **Testing:**
    *   Execute the defined tests for the deployed application, including API endpoints.
    *   Inform the user of the result, including the Space URL.

### 4.3. `Plan` Workflow

1.  **Project Scoping:**
    *   Define the project's scope and decide on the implementation strategy (direct file writing vs. `jules-agent`).
2.  **QA and Refinement:**
    *   Conduct a QA session with the user to clarify requirements.
    *   Reflect on user feedback and update the plan.
3.  **Task Creation:**
    *   Use `taskmaster-agent` to create and manage tasks and tests.
4.  **User Approval:**
    *   Request user approval for the final plan before execution.

### 4.4. Other Workflows

*   **`Run`:** Clone a repo, understand its build process, run it, and test use cases.
*   **`Adapt`:** Use the `Plan` workflow to manage changes to an existing codebase.
*   **`Ideate`:** A dedicated workflow for brainstorming and logging ideas.
*   **`Research`:** A workflow for conducting research.
*   **`Test`:** A workflow for creating and running tests.

## 5. Function and Tool Implementation

### 5.1. New Functions

*   `initiate_ideate_session()`: Starts the ideation workflow.
*   `taskmaster_function()`: Interacts with the `taskmaster-agent`.
*   `git_or_jules()`: A decision function to route tasks to either `git-agent` or `jules-agent`.
*   `get_space_logs_sse()`: A function to stream logs from Hugging Face Spaces.

### 5.2. External Tool Integration

*   **`SWE-agent`:** Adapt relevant files and concepts from `https://github.com/SWE-agent/SWE-agent.git`.
*   **`mermaid-js`:** Integrate `https://github.com/mermaid-js/mermaid.git` for diagramming.
*   **`todo.ai`:** Implement `https://github.com/fxstein/todo.ai.git` as the backend for `taskmaster-agent`.
*   **`swarmtask`:** Investigate and implement `https://github.com/rdhillbb/swarmtask.git` for parallel task execution.

## 6. Task Breakdown (Implementation Plan)

### Phase 1: Foundation and Agent Profiles

1.  **Create `task.md` file:** Create and save this `task.md` file in the repository root.
2.  **Update Developer Agent Profile:**
    *   Locate the system prompt for the `developer-agent`.
    *   Replace it with the new system prompt.
3.  **Sub-agent Scaffolding:**
    *   Create placeholder profiles/prompts for the new sub-agents: `monitor-agent`, `research-agent`, `taskmaster-agent`.
    *   Ensure they can be called by the main `developer-agent`.

### Phase 2: Core `Plan` and `Deploy` Workflows

4.  **Implement `Plan` Workflow:**
    *   Implement the QA session logic (raising a question sheet).
    *   Implement the reflection loop.
5.  **Integrate `todo.ai` for Taskmaster:**
    *   Clone the `todo.ai` repository.
    *   Adapt its functionality to be used by the `taskmaster-agent`.
    *   Create the `taskmaster_function()`.
6.  **Implement `Deploy` Workflow:**
    *   Implement the `huggingface-agent`'s ability to create spaces and upload files.
    *   Create the `monitor-agent` and the `get_space_logs_sse()` function to retrieve logs.

### Phase 3: Advanced Workflows and Tooling

7.  **Implement `Develop` Workflow:**
    *   Implement the `initiate_ideate_session()` function.
    *   Automate the log analysis and research steps.
8.  **Integrate `mermaid-js`:**
    *   Find a way to use `mermaid-js` to generate diagrams from text descriptions.
    *   Add a function to the `developer-agent` to create and save these diagrams.
9.  **Implement `git_or_jules()` Decision Function:**
    *   Create the logic to decide between `git-agent` and `jules-agent` based on the complexity of the task.

### Phase 4: Parallelism and Finalization

10. **Integrate `swarmtask`:**
    *   Investigate the `swarmtask` repository.
    *   Implement the `task_manager_subagent` to handle parallel and sequential task execution.
11. **Implement Remaining Workflows:**
    *   Implement the `Run`, `Adapt`, `Ideate`, `Research`, and `Test` workflows.
12. **Testing and Documentation:**
    *   Thoroughly test all new functionalities and workflows.
    *   Update the main `README.md` to document the new SWE Developer Agent and its usage.
13. **Pre-commit steps:**
    *   Ensure proper testing, verification, review, and reflection are done.
14. **Submit:**
    *   Submit the final changes.
