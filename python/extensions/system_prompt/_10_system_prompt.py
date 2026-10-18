from typing import Any
from python.helpers.extension import Extension
from python.helpers.mcp_handler import MCPConfig
from agent import Agent, LoopData


class SystemPrompt(Extension):

    async def execute(self, system_prompt: list[str] = [], loop_data: LoopData = LoopData(), **kwargs: Any):
        # append main system prompt and tools
        main = get_main_prompt(self.agent)
        tools = get_tools_prompt(self.agent)
        mcp_tools = get_mcp_tools_prompt(self.agent)
        
        # CUSTOM INSTRUCTIONS FOR THIS DEPLOYMENT
        # These instructions apply to all deployed spaces (Leon4gr45/agent, Leon4gr45/openoperator, etc.)
        custom_instructions = """
=== CUSTOM DEPLOYMENT INSTRUCTIONS ===

1. CODE EXECUTION:
   - ALWAYS use the `python` command (NOT ipython) for executing Python code
   - All code execution must happen in the `/app` directory
   - When creating files, use absolute paths starting with `/app/`
   - When running Python scripts, use: `python /app/path/to/script.py`
   - The working directory is `/app` - use relative paths from there when appropriate
   - Example: `python /app/scripts/my_script.py` or `python -c "print('hello')"`

2. WEB SEARCHES:
   - ALWAYS use the `search_engine` tool for ALL web searches
   - Do NOT use browser tools or other search methods
   - The search_engine tool uses SearXNG for privacy-preserving searches
   - Categories available: general, science, it, news, images, videos (use "general" if unsure)
   - Example: search_engine(query="latest AI news", category="general", num_results=5)

3. FILE OPERATIONS:
   - All files should be created/modified within `/app` folder
   - Use absolute paths like `/app/data/file.txt` when specifying locations
   - The `/app` folder persists and is the working directory
   - Check existing files in `/app` before creating new ones to avoid duplicates

4. FINAL RESPONSE:
   - When you are done with the task, use the 'response' tool to return the final answer

=== END CUSTOM INSTRUCTIONS ===
"""
        
        final_instruction = "When you are done with the task, use the 'response' tool to return the final answer."

        system_prompt.append(main)
        system_prompt.append(tools)
        if mcp_tools:
            system_prompt.append(mcp_tools)
        system_prompt.append(custom_instructions)
        system_prompt.append(final_instruction)


def get_main_prompt(agent: Agent):
    return agent.read_prompt("agent.system.main.md")


def get_tools_prompt(agent: Agent):
    prompt = agent.read_prompt("agent.system.tools.md")
    if agent.config.chat_model.vision:
        prompt += '\n\n' + agent.read_prompt("agent.system.tools_vision.md")
    return prompt


def get_mcp_tools_prompt(agent: Agent):
    mcp_config = MCPConfig.get_instance()
    if mcp_config.servers:
        pre_progress = agent.context.log.progress
        agent.context.log.set_progress("Collecting MCP tools") # MCP might be initializing, better inform via progress bar
        tools = MCPConfig.get_instance().get_tools_prompt()
        agent.context.log.set_progress(pre_progress) # return original
        return tools
    return ""
