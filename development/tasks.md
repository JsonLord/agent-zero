

# **1. Core System & Subagents**

### **1.1 Developer Agent = “Coding Planner + SWE‑Agent Hybrid”**
The developer agent is not just a coder — it is a **project orchestrator** with SWE‑agent‑style autonomy. It must:
- Understand multi‑step software development workflows  
- Break down tasks into components  
- Decide when to call subagents  
- Write files directly  
- Use planning logic when >2 files are involved  
- Maintain internal state across ideation → planning → tasking → deployment → testing  

>*(From task_context.md, section "Sheet For: Developer agent")*
>Replace the system prompt for the developer agent with a new system prompt and add capabilities and knowledge that represents it as a SWE agent.

### **1.2 Behavioral Expectations**
The developer agent must:
- Think like a senior engineer  
- Justify decisions  
- Prefer GitHub‑based changes over local ones  
- Use Jules-agent for complex or multi-file changes  
- Use Git-agent for simple, atomic edits  
- Use Huggingface-agent for anything involving Spaces  
- Use Monitor-agent to validate deployments  
- Use Taskmaster-agent to structure tasks and tests  

>*(From task_context.md, section "System prompt")*
>As a Coding Planner, the agent will utilise subagents to achieve tasks. It can write files itself using `write_file()` but must utilize the Plan prompt if more than 2 files need to be edited. The agent should prefer making changes on a GitHub repo rather than locally, unless the changes are related to Hugging Face deployment. Huggingface for huggingface-related tasks, git-agent for managing repos and make simple changes to one file, and jules-agent for working on specific components, make adaptations to project files for the project, with progress saved on github, not for local files. deploying files on huggingface can involve making changes to the dockerfile or space related files, that e,.g. clone a github repo and build it inside huggingface spaces. but huggingface agent has clear instructions. you can ask subagents for judgement on matters. monitor agent can retrieve logs from huggingface and jules taskmaster can clarify a list of tasks and tests to be done for development processes.

### **1.3 Subagent Roles (More Specific)**

#### **git-agent**
- Makes small, atomic edits (≤2 files)  
- Creates branches, commits, and pushes
- Reads repo structure using a `filemap`-like tool for structured overviews.
- Answers questions about build/run instructions  
- Incorporates on-the-fly `linting` into file editing workflows.

#### **jules-agent**
- Handles complex changes (≥3 files or ≥3 tasks)  
- Writes new components and refactors codebases
- Runs its own tests automatically
- Works on specific components and adapts project files on GitHub, not locally.
- Never receives secrets.
- Incorporates on-the-fly `linting` into file editing workflows.

#### **huggingface-agent**
- Creates Spaces and manages their configuration (Dockerfiles, app.py, etc.)
- Uploads files to Spaces and triggers rebuilds
- Handles secrets via Dockerfile ENV variables.

#### **monitor-agent**
- Retrieves Huggingface and Jules logs.
- Detects build and runtime failures.
- Reports status back to developer agent.

#### **research-agent**
- Searches GitHub + Huggingface for reusable components.
- Implements a `code_search` tool for deep analysis of code repositories.
- Returns up to 100 candidates, annotated with purpose, integration difficulty, licensing, and API availability.

#### **taskmaster-agent**
- **User-facing agent for task definition.**
- Converts plans into structured tasks and test goals.
- Maintains a dependency graph.

#### **task_manager_subagent**
- **Asynchronous background worker for task execution.**
- Not visible in the chat UI.
- Executes tasks in the correct order based on dependencies.
- Handles parallel vs. sequential execution.
- Reassigns tasks after failures and triggers tests automatically.

---

# **2. Tooling & Integrations**

### **2.1 Task Management (`todo.ai`)**
- **Goal:** Implement the `taskmaster-agent`'s functionality.
- **Implementation:**
    - A new tool will be created at `python/tools/taskmaster_tool.py`.
    - This tool will be a Python wrapper that executes the `todo.bash` script from the `todo.ai` repository (https://github.com/fxstein/todo.ai.git) as a command-line process.
    - It will pass task management commands (e.g., `add`, `list`) as arguments and return the output.
    - The `taskmaster-agent`'s prompt will be updated to use this new tool.

### **2.2 Parallel Task Execution (`swarmtask`)**
- **Goal:** Implement parallel execution for the `task_manager_subagent`.
- **Implementation:**
    - A new tool will be created at `python/tools/swarmtask_tool.py`.
    - This tool will be a Python wrapper for the `launchswarm.sh` script from the `swarmtask` repository (https://github.com/rdhillbb/swarmtask.git).
    - It will accept a JSON object of commands to be run in parallel, execute the script, and monitor for completion.

### **2.3 Diagramming (`mermaid`)**
- **Goal:** Enable the developer agent to generate diagrams.
- **Implementation:**
    - A new tool will be created at `python/tools/diagram_tool.py`.
    - The tool's `execute` method will first check if the `mmdc` command is available on the system. If not, it will run `npm install -g @mermaid-js/mermaid-cli` to install it. It will then take Mermaid syntax as input, write it to a temporary file, and execute `mmdc -i <temp_file> -o <output_file.svg>`. The SVG content will be returned.

### **2.4 Linting & Formatting (`ruff`)**
- **Goal:** Implement a project-wide linting and formatting setup to ensure high code quality, mirroring the best practices from the `SWE-agent` repository.
- **Implementation:**
    - Add `ruff` to the project's `pyproject.toml` as a development dependency.
    - Create a `ruff.toml` configuration file with rules similar to those in `SWE-agent`.
    - Add a script to the `pyproject.toml` to run `ruff check .` and `ruff format .`.
    - Integrate `ruff` into the pre-commit hooks.

---

# **3. Core Pipelines & Workflows**

### **3.1 Ideation Pipeline**
- **Trigger:** `initiate_ideate_session()` function.
- **Behavior:**
    1. Creates and logs every message of the session in `/app/ideate/{project_name_session_number}`.
    2. Encourages brainstorming, research, and architectural exploration.
    3. Upon conclusion of the session, automatically triggers an upload of the session log to the `JsonLord/agent-notes/logs` GitHub repository.
    4. Automatically triggers post-ideation steps upon completion.

>*(From task_context.md, section "Develop")*
>Ideate session including calling research agent, investigating git directories, finding suitable solutions, and critically reflect on ideas mentioned during an ideation session. the ideation session should be logged, so all conversation should be written to a file in /app directory.

- **Post-Ideation Steps:**
    1. Log is uploaded to `JsonLord/agent-notes/logs`.
    2. Developer agent analyzes the log to extract components and identify research candidates.
    3. `research-agent` searches for reusable code based on the analysis.
    4. `git-agent` + `huggingface-agent` evaluate the findings for feasibility and recommend integration strategies, presenting the final recommendations to the user via a `message_user` call (standard chat message).

>*(From task_context.md, section "Develop")*
>Once The session completes: The following functions should be kicked off automatically. Use llm by by mimicking a user message and wait for the chat to answer. The mimicked user message shall appear in the ui.
>1) the log file should be uploaded to github JsonLord/agent-notes/logs
>2) The developer is kicked off to analyse the log script and make notes, questions, annotations, grouping together specific aspects for which an external service is needed, or which could be replaced by a huggingface space or github project that has already created a code needed to fulfill this part of the code project. It should basically unfold the idea into components that fulfill specific purposes.
>3) Research agent shall be given the list of notes that concern the possible huggingface space or github code replacements for components. It should look for up to 100 possible findings.
>4) git-agent and huggingface agent shall then analyse the findings from the research agent regarding their match and if that code could be implemented, and how it could be implemented, by making it part of the main code, or by making it an external component. The two agents shall give their recommendations based on the analysis into the ui.

### **3.2 Planning Pipeline**
- **Behavior:**
    1. The agent breaks the project into components and identifies dependencies.
    2. It generates a "question sheet" for the user to resolve ambiguities. This will be a blocking interaction, using the `request_user_input` tool, which should be presented to the user as a modal pop-up.
    3. It reflects on the answers, with a maximum of 3 reflection loops, before signaling "All Clear" via a `message_user` call.
- **Output:** A plan file including components, dependencies, services needed, deployment strategy, and a Mermaid diagram.

>*(From task_context.md, section "Plan")*
>Write a plan file about the project and Then QA session starts. The developer agent raises a question sheet in a pop up message to the user and waits for answers for the questions. It then reflects on it, reworking a log file third edition. if components are still unclear, research, and if decisions are still unclear, or coming up based on that research and reflection, raise another question sheet to the user, or if not, raise a message: “All Clear, Tasks will be generated”. Set reflection loops to max=3, but hopefully the agent reflects well if no more decisions are unclear,. what can be interpreted shall be interpreted or researched before writing a questions. Only decisions that cannot be done based on research or thinking, shall be raised. Plan how a deployment on huggingface could look like, if apis are required, gradio is best, but custom apis can also be built into docker.

### **3.3 GitHub Integration**
- **Log Uploads:** All ideation and planning logs are uploaded to `JsonLord/agent-notes/logs`.
- **Repo Modifications:**
    - `git-agent` handles small edits (≤2 files).
    - `jules-agent` handles large edits (≥3 files).
    - The developer agent must specify file paths, exact changes, branch names, and commit messages.

### **3.4 Huggingface Deployment Pipeline**
- **Workflow:**
    1. `huggingface-agent` creates the space.
    2. The agent determines if it's a "GitHub app" or "Custom app" deployment.
    3. For GitHub apps, a Dockerfile with `git clone` is created. For custom apps, the Plan function or `jules-agent` is used.
    4. After uploading files, `monitor-agent` checks logs.
    5. The system tests endpoints and validates the UI before notifying the user with a final status update via `message_user`.
- **Secrets:** Secrets are never sent to `jules-agent` and are handled via Dockerfile ENV variables. If secrets are required, the agent will inform the user via a `message_user` call.

>*(From task_context.md, section "Deploy")*
>Create a new space with sdk based on requirements of the prompt project. Either custom or github app. Clarified in user prompt. When github: usually docker. investigate github repo with git-agent Create a dockerfile or app file or start file to deploy that app on the huggingface space by implementing a git clone command into the file. Then add a README.md file if custom: use Plan function() to plan the project’s scope and decide: either write files, or give jules-agent to write the project, upload to github, and you clone that project during build process, based on the scope of the project, the bigger, the better to ask jules. answer the plan function agent if it raises questions With the results from plan function, retrieve information about the tasks and tests it refined and implement the tasks via the specified agent and run the tests. Make sure to add a task that is called: API endpoint refinement, if one needs to communicate with the space or it is a gradio app to be deployed. then define the api endpoints for capabilities that should be communicated with, and add to the test section what endpoints need to be tested after successful deployment and that the space shows “running”. if all tests completed, deploy the full app on hugginface by utilising hugginface agent for the upload. – follow the deployment sheet. wait 5 minutes. ask monitor agent to retrieve the logs about the space and if it failed, fix and push changes, until it runs, giving it the parameters it needs. If it runs, go through test list and write a test code for the test, and if it fails, judge whether it fails because of the test script of the code, and take action, until the test succeeds. If it runs, and it has api endpoints, test these react to any failures and update the space files Inform the user that the app runs on … space link via message. if it fals because of secrets to be added to the space, inform user via message.

---

# **4. Supporting Systems**

### **4.1 Task Manager System**
- **Task Categories:** All tasks are classified as Deploy, Plan, Research, Build-in-steps, API-Endpoints, Build, or Last Features.
- **Task Requirements:** Each task must include a description, dependencies, a parallel/sequential tag, a test goal, and the required agent.
- **Execution Rules:** Parallel tasks run first. Failed tests are given the highest priority. The `task_manager_subagent` loops until all tests pass.

>*(From task_context.md, section "If the user writes: Continue the process by Generating the Tasks:")*
>The developer agent shall create tasks based on the log file components. It should leverage the [sequential_thinking] tool to think about tasks to be given to the task manager in the following order: These are: Deploy, Plan, Research, Build-in-steps, API-Endpoints, Build, Last features. For each Task the agent shall remark a test, how a successful test would look like, and what the test needs to validate for this task to be implemented successful. The developer agent then assign an agent to run these tests, or group agents together tp run tests together. e.g. a huggingface deployment of a gradio app must see that the logs show that the space is running, but also that all of the gradio api endpoints are working correctly. Whereas with components for a code project, the jules agent needs to validate that this components works as intended, and then later the test needs to to validate that the component works in combination with the others. (jules_agent usually tests automatically, so when it is given tasks, just include a section for testing. it writes its own tests and reports back on them) - implement a level system (e.g. paralell on level 1, or level 2 and level 2 requires components …, and so on.) Check the to do list to be complete, and each task to have a test defined, no test script written yet, but a test goal defined. And give each task a tag: needs to be sequential, and which order in the sequence (on what does this component builds up on and what requires this component), parallel (this component can be built in parallel because no other components required).

### **4.2 Testing System**
- **Test Generation:** Tests are derived from tasks and must include a clear test goal and success criteria. The system should detect potential new use cases and ask the user for confirmation before adding them to the test suite, using the `request_user_input` tool (modal pop-up).
- **Test Execution:** The developer agent writes tests, `jules-agent` runs component tests, `huggingface-agent` tests endpoints, and `monitor-agent` checks logs.
- **Failure Handling:** Failed tests immediately generate new, high-priority tasks for the developer agent to fix.

### **4.3 Adaptation System**
- **Behavior:** When adapting a codebase, the agent uses the Plan sheet to break changes into tasks, uses the appropriate agent (`git` or `jules`) to apply them, re-tests, and updates logs.

### **4.4 Run Mode**
- **Behavior:** The agent clones a repo, asks `git-agent` how to run it, identifies use cases, tests them, and uses the `request_user_input` tool (modal pop-up) to ask the user if failures should be fixed before engaging the Adaptation System.

---

# **5. Architectural Principles**

### **5.1 Keyword-Triggered Personas**
- **Mechanism:** A new extension in `python/extensions/message_loop_prompts_before/` will inspect the user's message for keywords (e.g., `Develop`, `Deploy`, `Plan`).
- **Logic:** If a keyword is detected, a "persona prompt" is prepended to the user's message, instructing the agent to adopt a specific role, toolset, and workflow.

### **5.2 Key Decision Functions**
- **`git_or_jules()` Decision:** This is the primary gate for all code modification tasks and must be implemented as a robust, automated function.
- **HF Deployment Strategy Decision:** A critical fork in the deployment workflow. The agent must explicitly choose between a "GitHub App" or a "Custom App" at the start of a deployment task, likely prompted by a `request_user_input` call.
- **Component Integration Decision:** A "Go/No-Go" decision point. The agent must present a clear summary of pros and cons for integrating external code and require user approval via a `request_user_input` call (modal pop-up).

### **5.3 Architectural Optimizations & Considerations**
- **State Management:** Implement a formal state machine to manage the agent's context across pipelines.
- **Robust Error Handling:** Implement a standardized error handling and retry mechanism with exponential backoff and a dead-letter queue for failed tasks.
- **Centralized Configuration:** Use a `config.yaml` file for project-specific configurations.
- **Enhanced Security for `jules-agent`:** Implement a "secrets scrubber" validation layer to prevent secrets from being passed to the `jules-agent`.
- **UI Feedback Mechanism:** Implement a standardized service for sending status updates and notifications to the UI via the `message_user` tool.

### **5.4 Log Differentiation**
- **Application Logs:** These are logs fetched by the `monitor-agent` from remote API endpoints (e.g., from a Hugging Face Space). They represent the runtime output of a deployed application.
- **Session Logs:** These are local conversation records created by the `developer-agent` in the `/app/ideate/` directory during an ideation session. They contain the full transcript of the interaction between the user and the agent.


