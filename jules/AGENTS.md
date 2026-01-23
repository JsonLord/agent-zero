Working behaviour and prompt context for Jules. how to follow the instructions in the other files and how to use the context for the task at hand. 
Add: to never delete a hf_upload.py file once created. And always reuse that before testing the logs, then testing apis for functionality. Then submit with summary of final results, of the space and the functionalities. 

Agent behaviour: Scan vision of project, scan the repos asociated, scan the task list. Build component by component. Test components. Identify where components interact. Test the internal interaction. Build the functionality FastAPI endpoint for each feature to later be tested via api once deployed. Then test the overall app from start to finish. Then make the deployment files and script for the huggingface deployment based on the /deployment folder and huggingface space parameters. Then expose the FASTAPis in the way it is recommended. Gradio=gradio endpoints. Docker= space url endpoints /health etc. Then deploy. Then check the build logs, then the run logs. Fix failures until successfully running. Then check the exposed FastAPI endpoints for functionality if no Auth tokens for the app are needed. If they are needed. Submit once the app is running and wait for the user to enter the space secrets, and test then. 


## important!
The current codebase you are working in is to be adapted following the vision of the project transformation in the /jules folder. The current application should be kept and only slightly changed, improved, expanded by the features described in /jules folder. The tasks files give a starting point, but judge for yourself. Develop tests to run to first see the current application feature, how it is working and make a plan to implement the features requested in /jules folder to develop the current application inside the repo towards the vision described to achieve expansion of the current app with functionalities described in the /jules folder. Adapt your coding implemententation to the coding language used by the project, and try to go with that. Test the full app within this working space. 

See what huggingface sdk from gradio over streamlit to docker fits best and use that, configure the README.md file accordingly and prepare to upload the file app, not just the new features, but the full app expanded with these new features, to the huggingface space. Monitor deployment and once it is running, test the api endpoints you had set to see the functionality of the app inside that huggingface space.

## Project Specific Instructions
Here’s a structured **AGENTS.md** section tailored for the **Agent Zero A2A (Agent-to-Agent) functionality**, incorporating all extracted context, tasks, and deployment specifics:

---

```markdown
# AGENTS.md: Agent Zero A2A (Agent-to-Agent) Functionality Guide
---
**Last Updated:** `<YYYY-MM-DD>`
**Applicable Repos:**
- [`agent0ai/agent-zero`](https://github.com/agent0ai/agent-zero) (Core)
- [`harvesthealth/agent-zero`](https://github.com/harvesthealth) (Custom Fork)

---

## **1. Overview**
This document outlines the **Agent-to-Agent (A2A)** communication protocol for Agent Zero, enabling direct API-driven interactions between agent instances. The goal is to:
- **Expose a robust HTTP MCP server** on Hugging Face Spaces.
- **Validate final-answer retrieval** without sub-agent noise.
- **Enable terminal streaming** for real-time output.
- **Ensure modularity** for distributed workflows.

---

## **2. Core Requirements**
### **2.1 API Endpoints**
| Endpoint       | Method | Purpose                                                                 | Input Format                                                                                     | Output Format                                                                                     |
|----------------|--------|-------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| `/mcp`         | POST   | Primary A2A message exchange.                                          | ```json { "message": "Query", "disable_subagents": true, "stream_terminal": true } ```           | ```json { "final_answer": "Result", "terminal_stream": ["output logs..."], "metadata": {...} } ``` |
| `/stream`      | POST   | Real-time terminal output streaming (optional).                        | Same as `/mcp` but focused on CLI output.                                                       | SSE/Chunked JSON lines.                                                                           |
| `/api/status`  | GET    | Health check and endpoint validation.                                   | None                                                                                              | ```json { "status": "online", "version": "0.9.4" } ```                                           |

### **2.2 Key Features**
- **Final Answer Only**: Responses exclude intermediate thoughts/sub-agent logs.
- **Terminal Streaming**: Enabled via `stream_terminal: true`.
- **Sub-Agent Bypass**: Controlled via `disable_subagents` flag in requests.
- **Error Handling**: Structured JSON errors (e.g., `{"error": "Invalid payload"}`).
- **Logging**: Middleware to track API interactions and terminal output.

---

## **3. Deployment Instructions**
### **3.1 Hugging Face Space Setup**
1. **Fork the Repository**
   - Clone `agent0ai/agent-zero` and push fixes to `harvesthealth/agent-zero`.
   - Ensure the fork includes:
     - Updated `server.py` (A2A endpoints).
     - Modified `prompts/default/agent.system.md` (API-specific instructions).
     - `config.yaml` with `streaming: true` and `logging: true`.

2. **Deploy to Space**
   - Use the `harvesthealth/agent-zero` repo in [HarvestHealth’s Space](https://harvesthealth-running-mcp-agent-backup.hf.space).
   - **Accelerator**: CPU-only (no GPU required).

3. **Exposed Endpoints**
   - Ensure `/mcp` and `/stream` are routed via `server.py`.

### **3.2 Configuration**
#### **`prompts/default/agent.system.md`**
```markdown
# API-Specific Instructions
IF "disable_subagents" is true in the API request:
  - Skip sub-agent delegation.
  - Return only the final answer.
  - Do not include intermediate logs or tool calls.

IF "stream_terminal" is true:
  - Capture and return command output in real-time.
  - Format as JSON lines: `{"type": "terminal", "content": "..."}`.
```

#### **`config.yaml`**
```yaml
streaming: true          # Enable terminal output streaming
logging: true            # Log API interactions and errors
api_keys:
  - "your_api_key_here"  # Restrict access
```

---

## **4. Testing Workflow**
### **4.1 API Validation**
| Test Case               | Input                                                                 | Expected Output                                                                                         | Success Criteria                                                                               |
|-------------------------|------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| **Final Answer Only**   | `POST /mcp` with `{"message": "Sum 2+2"}`                             | ```json { "final_answer": "4" } ```                                                                      | No sub-agent logs, only the final result.                                                      |
| **Terminal Stream**     | `POST /mcp` with `{"command": "ls", "stream_terminal": true}`         | ```json { "terminal_stream": ["file1.txt", "dir1/"] }