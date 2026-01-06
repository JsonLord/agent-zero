import pytest
import os
import json
from python.tools.taskmaster_tool import taskmaster_tool
from python.tools.swarmtask_tool import swarmtask_tool
from python.tools.diagram_generator import DiagramGenerator
from unittest.mock import MagicMock

# Test for the taskmaster_tool
def test_taskmaster_tool_list():
    """Tests the taskmaster_tool with the 'list' command."""
    output = taskmaster_tool("list")
    assert "Error" not in output
    # A basic check to see if it returns something that looks like a task list header
    assert "TODO" in output or "todo.ai" in output or "No tasks found" in output or "ID" in output

# Test for the new Python-based swarmtask_tool
def test_swarmtask_tool_python_implementation():
    """Tests the new Python-based swarmtask_tool."""
    tasks = {
        "task1": "echo hello from swarm",
        "task2": "sleep 1 && echo second task"
    }
    tasks_json = json.dumps(tasks)
    output_json = swarmtask_tool(tasks_json)
    results = json.loads(output_json)

    assert "task1" in results
    assert "task2" in results
    assert results["task1"]["status"] == "completed"
    assert "hello from swarm" in results["task1"]["output"]
    assert results["task2"]["status"] == "completed"
    assert "second task" in results["task2"]["output"]

# Test for the DiagramGenerator tool
@pytest.mark.asyncio
async def test_diagram_generator_tool():
    """Tests the DiagramGenerator tool's ability to create an SVG file."""
    # Mock the Tool's dependencies
    mock_agent = MagicMock()
    mock_loop_data = {}

    tool = DiagramGenerator(
        agent=mock_agent,
        name="DiagramGenerator",
        method=None,
        args={},
        message="Generating diagram",
        loop_data=mock_loop_data
    )

    mermaid_syntax = "graph TD; A-->B;"
    output_path = "tmp/test_diagram.svg"

    # Clean up any previous test file
    if os.path.exists(output_path):
        os.remove(output_path)

    response = await tool.execute(mermaid_syntax, output_path=output_path)

    assert "Error" not in response.message
    assert os.path.exists(output_path)

    # Clean up the generated file
    os.remove(output_path)
