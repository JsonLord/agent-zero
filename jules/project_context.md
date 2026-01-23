# Project Context

## Project Description
**Project Description: Adaptation and Improvement of Agent Zero’s A2A (Agent-to-Agent) Functionality**

---

### **Vision**
The **Agent Zero A2A (Agent-to-Agent) functionality** is being refined to enable seamless, direct API communication between agent instances—specifically validating and deploying the **HTTP MCP (Multi-Agent Communication Protocol) server** on Hugging Face Spaces. The goal is to ensure:
- **Direct final-answer retrieval** via API (excluding intermediate thoughts or sub-agent progress).
- **Terminal output streaming** (if enabled) for real-time interaction.
- **Robust error handling**, logging, and deployment stability.

This aligns with Agent Zero’s core philosophy of **modularity, extensibility, and organic growth**, where agents dynamically collaborate while maintaining transparency and control.

---

### **Concrete Goals**
1. **API Compatibility Validation**:
   - Test `/mcp` or `/stream` endpoints for message serialization/deserialization.
   - Ensure responses contain **only the final answer** (not sub-agent logs or intermediate steps).
   - Validate **terminal stream capture** for commands like `ls` or `python --version`.

2. **Sub-Agent Delegation Control**:
   - Modify the **system prompt** (`prompts/default/agent.system.md`) to bypass sub-agent creation for API-driven tasks via a `disable_subagents` flag.
   - Test with dedicated "API-only" agent roles to isolate behavior.

3. **Deployment and Monitoring**:
   - Update Hugging Face Space configuration (`server.py`, `config.yaml`) to expose MCP endpoints and enable streaming.
   - Deploy fixes to [HarvestHealth’s Space](https://harvesthealth-running-mcp-agent-backup.hf.space) and monitor logs for errors or unexpected behavior.

4. **Error Handling and Logging**:
   - Implement middleware to log API interactions and terminal output.
   - Test edge cases (e.g., malformed requests, long-running commands) for graceful degradation.

---

### **Future Use Cases**
- **Distributed AI Workflows**:
  Integrate Agent Zero instances across cloud environments (e.g., Hugging Face Spaces, local Docker) for collaborative task execution, where one agent orchestrates subtasks across others via A2A.
  *Example*: A central agent delegates data analysis to a specialized "Data Scientist" agent on another Space, then aggregates results.

- **Hybrid Human-Agent Systems**:
  Enable **real-time API-driven interactions** between Agent Zero and external tools (e.g., web scraping agents, database query agents) without exposing sub-agent internals.
  *Example*: A user queries an agent via API to summarize a document, and the agent retrieves the final summary—no need to parse logs.

- **Agent Marketplaces**:
  Deploy specialized agents (e.g., "Code Reviewer," "Legal Analyst") as independent A2A services, where users invoke them via standardized API calls without managing infrastructure.
  *Example*: A developer calls an "Automated Tester" agent via `/mcp` to generate unit tests and downloads the final output.

- **Edge Device Integration**:
  Lightweight Agent Zero instances could run on edge devices (e.g., Raspberry Pi), communicating with a central "Master" agent via A2A for tasks like IoT monitoring or local automation.
  *Example*: A home security agent on a Pi sends alerts to a cloud-based "Security Coordinator" agent via MCP.

---

### **Potential Integrations**
1. **Existing Agent Zero Features**:
   - **Tools Extension**: A2A can be treated as a **custom tool** (e.g., `python/tools/mcp_tool.py`) for agent-to-agent communication.
   - **Prompt Customization**: System prompts can enforce A2A-specific behavior (e.g., "Only return final answers to API calls").
   - **Memory Sharing**: Agents could exchange **filtered memories** via A2A (e.g., "Here’s what I learned about X").

2. **External Protocols**:
   - **MCP Standardization**: Align with the [Agent-to-Agent Communication Protocol](https://github.com/agent0ai/agent-zero/tree/main/docs/connectivity.md) to ensure interoperability with other frameworks (e.g., AutoGen, CrewAI).
   - **WebSockets**: For low-latency streaming between agents in real-time applications.
   - **gRPC**: For high-performance, microservices-like agent communication.

3. **Deployment Platforms**:
   - **Hugging Face Spaces**: Hosted lightweight A2A endpoints with serverless scalability.
   - **Docker/Kubernetes**: Containerized agents with dynamic service discovery.
   - **Local Networks**: A2A over LAN for offline or air-gapped systems.

4. **UI/UX Enhancements**:
   - **Terminal Stream Visualization**: Display real-time terminal output in the Web UI for API-driven commands.
   - **API Playground**: A built-in interface to test A2A endpoints with preconfigured examples (e.g., "Call a remote agent to summarize this file").
   - **Agent Roles Dashboard**: Visualize agent hierarchies and A2A connections in the Web UI.

---
### **Key Improvements in Recent Versions**
- **v0.9.4+**:
  - **Streamable HTTP MCP Server**: Native support for A2A via HTTP endpoints.
  - **Subordinate Agent Isolation**: Dedicated prompts/tools for API-only roles.
  - **Rate Limiting**: Prevents API abuse during high-load interactions.
  - **Delayed Memory Recall**: Optimizes A2A communication by filtering relevant memories.

- **v0.9.0**:
  - **Backup/Restore**: Simplifies deploying A2A configurations across environments.
  - **Agent Roles**: Enables specialized A2A agents (e.g., "API Proxy" for external systems).

---
### **Challenges and Mitigations**
| **Challenge**               | **Mitigation Strategy**                                                                 |
|-----------------------------|----------------------------------------------------------------------------------------|
| Sub-agent interference       | System prompt flag (`disable_subagents`) for API calls.                                |
| Terminal stream corruption  | Enforce JSON-line format for logs; validate before serialization.                     |
| API schema mismatches        | Implement backward-compatible schemas with deprecation warnings.                        |
| Latency in distributed calls| Use lightweight A2A agents with cached tools (e.g., pre-loaded prompts).              |
| Security risks               | Restrict API keys to read-only or scoped permissions for sensitive operations.        |

---
### **Roadmap**
1. **Short-Term (v0.9.x)**:
   - Finalize A2A API specs (e.g., `/mcp` payload structure).
   - Deploy to Hugging Face Space with logging/monitoring.
   - Add UI controls for A2A settings (e.g., "Stream terminal output").

2. **Mid-Term (v1.0)**:
   - **Agent Marketplace**: Publish tools/plugins as A2A services.
   - **Multi-Modal A2A**: Extend to video/audio agents (e.g., summarizing meetings via API).
   - **Authentication**: OAuth/JWT for secure agent-to-agent interactions.

3. **Long-Term**:
   - **Federated Learning**: Agents share anonymized insights via A2A without central servers.
   - **Autonomous Orchestration**: Agent Zero auto-discovers and composes A2A services for complex tasks.
   - **Standardization**: Propose A2A as a de facto protocol for the AI community.

---
### **Example Workflow**
**User Query via API**:
```json
POST /mcp
{
  "message": "Analyze this data: [file.csv]",
  "disable_subagents": true,
  "stream_terminal": true,
  "tools": ["pandas", "matplotlib"]
}
```
**Agent Zero Response**:
```json
{
  "final_answer": "The dataset shows a 12% increase in Q3 sales.",
  "terminal_stream": [
    "Loading data...",
    "Generating plot: [output.png]",
    "Analysis complete."
  ],
  "metadata": {
    "tools_used": ["pandas", "matplotlib"],
    "memory_id": "abc123"
  }
}
```

---
**Core Philosophy**:
Agent Zero’s A2A functionality embodies its **"computer as a tool"** ethos—agents should **collaborate as dynamically as humans do**, without predefined constraints. The API becomes another **interactive surface** for organic growth.

## Tasks and Tests
### **Extracted Tasks and Tests (7-Point Template)**

---

#### **1. Estimation of Project Scope (1-10):**
**Core Scope Breakdown (10/10 for full API validation + deployment)**
- **API Testing & Fixing (7/10)**: Validate `/mcp` or `/stream` endpoints, message serialization, and terminal streaming.
- **Sub-Agent Bypass (3/10)**: Modify system prompt or agent role to disable sub-agent delegation for API calls.
- **Deployment & Monitoring (5/10)**: Update Hugging Face Space, log monitoring, and edge-case testing.

---

#### **2. Project Description**
**Vision**:
Ensure the Hugging Face Space-hosted Agent Zero instance (`harvesthealth-running-mcp-agent-backup.hf.space`) supports **direct A2A API calls** that:
- Return **only the final answer** (not intermediate thoughts/sub-agent progress).
- Capture and stream **terminal output** if enabled.
- Handle errors gracefully and log interactions for debugging.

**Concrete Goals**:
- Validate `/mcp` or `/stream` API endpoints for compatibility with Hugging Face Spaces.
- Modify Agent Zero’s **system prompt** to bypass sub-agent delegation for API-driven tasks.
- Deploy fixes to the Space and monitor logs for stability.

**Future Use Cases**:
- **Distributed agent networks**: Use A2A to orchestrate multi-agent workflows across Spaces.
- **Automated testing**: Integrate with CI/CD pipelines for Agent Zero upgrades.
- **Voice/STT integrations**: Stream terminal output to voice assistants (e.g., via WebSocket).

**Future Integrations**:
- **External APIs**: Connect Agent Zero to tools like **MCP servers**, **LiteLLM providers**, or **custom Python tools**.
- **Hugging Face Hub**: Share agent configurations (prompts/tools) as reusable models.
- **WebSocket**: Enable real-time terminal streaming for remote debugging.

---

#### **3. External Projects/APIs to Integrate**
| **Component**               | **Purpose**                                                                 | **Integration Notes**                                                                                     |
|-----------------------------|-----------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| **Hugging Face Spaces**     | Hosting the MCP server instance.                                            | Use `/mcp` endpoint for A2A communication; ensure `server.py` exposes routes correctly.                   |
| **Agent Zero Core**         | Modular tools/prompts for A2A behavior.                                     | Update `prompts/default/agent.system.md` to disable sub-agents for API calls.                            |
| **LiteLLM**                 | LLM provider abstraction (supports OpenRouter, Azure, etc.).                | Verify API logs work with LiteLLM’s streaming responses.                                                |
| **Mermaid CLI**             | Generate diagrams for terminal output (e.g., file structures).               | Ensure terminal streams include Markdown-compatible formatting.                                          |
| **SSE/WebSocket**           | Real-time terminal streaming (if `/mcp` doesn’t support it).               | Fallback to custom WebSocket endpoint if API limits streaming.                                           |
| **Loguru**                  | Logging middleware for API interactions.                                    | Add to `server.py` to track API calls, terminal output, and errors.                                      |
| **Postman/curl**            | API testing tools.                                                          | Predefined requests for validation (e.g., `POST /mcp` with `disable_subagents=true`).                   |

---

#### **4. Components & Subtasks**
##### **4.1 Core Components to Build/Integrate**
| **Component**               | **Type**          | **Interaction Protocol**                                                                                     |
|-----------------------------|-------------------|-------------------------------------------------------------------------------------------------------------|
| **A2A API Endpoint**        | New (Hugging Face Space route) | HTTP POST to `/mcp` or `/stream` with JSON payload (`message`, `disable_subagents`, `stream_terminal`).|
| **Sub-Agent Bypass Logic**  | Prompt modification | System prompt filter to ignore sub-agent delegation for API requests.                                |
| **Terminal Stream Capture** | Feature enhancement | Log terminal output to JSON lines or SSE format for API responses.                                        |
| **Error Handler**           | Middleware         | Validate payloads, return structured errors (e.g., `{"error": "Invalid command"}`).                       |
| **Logging System**          | Deployment tool    | Loguru middleware in `server.py` to track API calls and terminal output.                                  |

---

##### **4.2 Subtasks per Component**
###### **A2A API Endpoint**
- **Architecture**:
  - **Security**: Authenticate API calls (e.g., API keys in `config.yaml`).
  - **Functionality**: Support `POST /mcp` with body:
    ```json
    {
      "message": "Sum 2+2",
      "disable_subagents": true,
      "stream_terminal": true
    }
    ```
  - **Interaction**: Return final answer + terminal stream (if enabled) in JSON.
- **Integration**:
  - Clone `agent0ai/agent-zero` and inspect `server.py` for existing MCP server logic.
  - Merge with `harvesthealth` fork to expose `/mcp` route.
  - **Build Protocol**: Use FastAPI or Flask to handle POST requests; validate payload schema.

###### **Sub-Agent Bypass Logic**
- **Architecture**:
  - Modify `prompts/default/agent.system.md` to include:
    ```markdown
    IF "disable_subagents" is true in API request, bypass sub-agent delegation.
    ```
  - **Security**: Ensure API keys or headers override system prompt settings.
- **Integration**:
  - Update `python/tools/` to add a `tool_disabled` flag for sub-agents when `disable_subagents=true`.
  - **Judgement**: Full prompt modification needed; no partial integration possible.

###### **Terminal Stream Capture**
- **Architecture**:
  - **Protocol**: Capture terminal output as JSON lines or SSE chunks.
  - **Endpoint**: Add `/mcp/stream` to return live output (fallback to `/mcp` if not supported).
- **Integration**:
  - Modify `python/tools/terminal.py` to buffer output for API responses.
  - **Build Protocol**: Use `itertools` for chunked streaming or WebSocket for real-time.

###### **Error Handler**
- **Architecture**:
  - **Logging**: Loguru integration to track API errors (e.g., malformed requests).
  - **Response**: Standardize error messages (e.g., `400 Bad Request` with `{"error": "..."}`).
- **Integration**:
  - Add to `server.py` middleware; validate against API schema.

###### **Logging System**
- **Architecture**:
  - **Protocol**: Log API calls, terminal output, and agent actions to `logs/api_debug.log`.
  - **Format**: JSON with timestamps and payloads.
- **Integration**:
  - Install `loguru`; update `config.yaml` to enable logging.

---

##### **4.3 Tests per Component**
| **Component**               | **Test Description**                                                                                     | **Success Criteria**                                                                                     |
|-----------------------------|---------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| **A2A API Endpoint**        | Send `POST /mcp` with `{"message": "Hello"}`; check response status.                                  | Returns `200 OK` with `{"final_answer": "..."}`.                                                        |
| **Sub-Agent Bypass**        | Send `POST /mcp` with `{"disable_subagents": true}`; verify no sub-agent logs.                        | Response contains only final answer; no `sub-agent:` prefixes in logs.                                    |
| **Terminal Stream**         | Send `{"command": "ls"}`, check if response includes terminal output.                                  | Response includes `"terminal_stream": ["file1.txt", ...]`.                                                |
| **Error Handler**           | Send malformed JSON (e.g., `null`); verify error message.                                              | Returns `400 Bad Request` with `{"error": "Invalid payload"}`.                                         |
| **Logging System**          | Trigger API call; check `logs/api_debug.log` for recorded payload.                                     | Log contains timestamped JSON with `{"action": "api_call", "payload": {...}}`.                         |

---

#### **5. Full Pipeline Test**
**Test Description**:
Simulate an end-to-end A2A workflow:
1. **Input**: API call to Hugging Face Space with:
   ```json
   {
     "message": "Analyze this file: /tmp/report.txt",
     "disable_subagents": true,
     "stream_terminal": true
   }
   ```
2. **Output**:
   - **Final Answer**: `"The report contains 3 sections: Overview, Data, Conclusion."`
   - **Terminal Stream**: `[{"type": "command", "content": "cat /tmp/report.txt"}, {"type": "output", "content": "Section 1:..."}]`
3. **Mock Input Data**:
   ```bash
   # Simulated file content (for testing):
   echo "Section 1: Overview" > /tmp/report.txt
   echo "Section 2: Data" >> /tmp/report.txt
   ```

**Success Criteria**:
- API returns final answer **without sub-agent delegation**.
- Terminal stream is **captured and formatted** in the response.
- Logs show `API call completed successfully`.

---

#### **6. API Endpoints for Testing**
| **Endpoint**               | **Method** | **Description**                                                                                     | **FastAPI/Gradio Reference**                                                                 |
|-----------------------------|------------|----------------------------------------------------------------

## GitHub Repos
Here is the extracted list of GitHub repositories from the provided log:

1. **[agent0ai/agent-zero](https://github.com/agent0ai/agent-zero)**
2. **[harvesthealth](https://github.com/harvesthealth)** *(Custom fork, implied by the Hugging Face Space URL)*

## Functionality Expectations
### **Functionality Expectations of the Agent Zero A2A Deployed System**

#### **Core Requirements**
1. **Direct API Communication**
   - **Input/Output:** Accept API messages (JSON payloads) via HTTP (e.g., `/mcp` or `/stream`).
   - **Final Answer Only:** Return the **conclusive response** (not intermediate thoughts, tool calls, or sub-agent progress).
   - **Example:**
     ```json
     Input:  {"message": "What is 2+2?"}
     Output: {"final_answer": "4"}
     ```

2. **Terminal Stream Support (Optional)**
   - **Streaming:** Capture and return **real-time terminal output** (e.g., code execution, CLI commands) via API.
   - **Format:** Chunked or SSE responses with structured logs.
   - **Example:**
     ```json
     Input:  {"command": "ls", "stream_terminal": true}
     Output: [
       {"type": "terminal", "content": "$ ls"},
       {"type": "log", "content": "file1.txt  file2.txt"}
     ]
     ```

3. **Sub-Agent Isolation**
   - **Bypass Delegation:** For API-driven tasks, **disable sub-agent creation** to avoid cluttering responses.
   - **Flag:** Use a request parameter (e.g., `"disable_subagents": true`) or prompt-level instruction.

4. **Error Handling & Logging**
   - **Validation:** Reject malformed requests with clear error messages (e.g., `{"error": "Invalid payload"}`).
   - **Logging:** Middleware to track API calls, terminal streams, and failures for debugging.

5. **Hugging Face Space Compatibility**
   - **Endpoint Exposure:** Deploy `/mcp` or `/stream` routes via `server.py`.
   - **Configuration:** Enable streaming/logging in `config.yaml` and `prompts/default/agent.system.md`.
   - **Dependencies:** Include `mermaid-cli` and custom `python/tools/` for tool execution.

6. **Agent Zero Core Integrations**
   - **Prompts:** Modify system prompts to enforce API-specific behavior (e.g., "Return only final answers for API calls").
   - **Tools:** Ensure tools (e.g., code execution, search) are serializable via API.

7. **Monitoring & Edge Cases**
   - **Long-Running Tasks:** Handle timeouts and large payloads (e.g., file uploads/downloads).
   - **Rate Limiting:** Prevent abuse via API request throttling.

---
#### **Key Features to Validate**
| Feature               | Requirement                                                                 | Test Case                                                                 |
|-----------------------|---------------------------------------------------------------------------|--------------------------------------------------------------------------|
| **Final Answer Only** | API response excludes sub-agent logs/thoughts.                          | Input: `{"message": "Sum 1+1"}`, Output: `{"final_answer": "2"}`          |
| **Terminal Streaming**| Real-time CLI output accessible via API.                               | Input: `{"command": "echo hello", "stream_terminal": true}`              |
| **Sub-Agent Bypass**  | API calls do not trigger sub-agent creation unless explicitly allowed. | Input: `{"message": "Task", "disable_subagents": true}` → No sub-agents. |
| **Error Handling**    | API rejects invalid requests gracefully.                              | Input: `{"invalid": "key"}`, Output: `{"error": "Missing 'message' field"}` |
| **Logging**           | API interactions and terminal outputs are logged.                       | Check Hugging Face Space logs for `POST /mcp` entries.                  |

---
#### **Deployment-Specific Expectations**
- **Hugging Face Space:**
  - **Accelerator:** CPU-only (no GPU required for Agent Zero).
  - **Exposed Endpoints:** `/mcp` (HTTP MCP server) and `/stream` (if enabled).
  - **Files to Deploy:**
    - `server.py` (updated to handle A2A routes).
    - `prompts/default/agent.system.md` (API-specific instructions).
    - `config.yaml` (enable `streaming` and `logging` flags).
- **Custom Fork:**
  - Fork `agent0ai/agent-zero` → Push fixes to `harvesthealth/agent-zero` for Space deployment.

## API Endpoints
Here is the extracted list of **API endpoints** and their intended purposes based on the analysis:

1. **`/mcp` (HTTP MCP Server)**
   - **Purpose**: Core Agent-to-Agent (A2A) communication endpoint for sending/receiving messages.
   - **Methods**: `POST` (for message transmission), likely supports streaming (e.g., SSE or chunked responses).
   - **Input/Output**:
     - **Request Body** (JSON):
       ```json
       {
         "message": "Your task or query",
         "disable_subagents": true/false,  // Bypass sub-agent delegation if needed
         "stream_terminal": true/false    // Enable terminal output streaming
       }
       ```
     - **Expected Response**:
       ```json
       {
         "final_answer": "The concise result",
         "terminal_stream": ["$ ls", "file1.txt file2.txt"],  // If streaming enabled
         "error": "Description"  // Fallback for failures
       }
       ```
   - **Features**:
     - Message serialization/deserialization validation.
     - Terminal stream capture (real-time output).
     - Sub-agent delegation control.
     - Error handling and logging.

2. **`/stream` (Alternative Endpoint)**
   - **Purpose**: Streaming-specific endpoint (if separate from `/mcp`) for real-time terminal output.
   - **Methods**: Likely `GET`/`POST` with SSE/chunked responses.
   - **Use Case**: Capturing live terminal logs (e.g., command execution output).

3. **`/api` (Generic API Gateway)**
   - **Purpose**: May expose additional routes (e.g., status checks, configuration).
   - **Methods**: `GET` (for health/status), `POST` (for custom tools).
   - **Example**: `/api/status` → Returns agent uptime or endpoint availability.

---
### **Key Endpoint Behaviors**:
- **Final Answer Focus**: API must return only the **final output** (not intermediate thoughts/sub-agent logs) unless explicitly requested.
- **Terminal Streaming**: Enabled via `stream_terminal: true`, returning raw terminal output (e.g., `ls` commands, Python logs).
- **Sub-Agent Control**: Use `disable_subagents: true` to prevent delegation during API calls.
- **Serialization**: Input/output must validate JSON/MD formats to avoid parsing errors.
- **Error Handling**: Clear error messages (e.g., `{"error": "Invalid message"}`) for debugging.

---
### **Deployment Notes**:
- **Hugging Face Space**: Ensure `server.py` routes `/mcp` and `/stream` with logging middleware.
- **Config**: Update `prompts/default/agent.system.md` to enforce API-focused behavior (e.g., "disable sub-agents for API calls").
- **Dependencies**: Requires `mermaid-cli` (for diagramming) and custom `python/tools/` for tool extensibility.

## HF Deployment Data
Profile: `harvesthealth`
Space: agent-zero
