import re

with open("tests/test_a2a_argus_supervisor.py", "r") as f:
    content = f.read()

# Make initialize_agent and AgentContext fail if called
fixture = """
@pytest.fixture(autouse=True)
def guard_agent_zero_initialization():
    with patch("helpers.fasta2a_server.initialize_agent", side_effect=AssertionError("LLM/runtime path reached")), \
         patch("helpers.fasta2a_server.AgentContext", side_effect=AssertionError("AgentContext path reached")):
        yield
"""

# But wait, test_ordinary_message_goes_to_agent_zero WILL call them, so we need a way to mock them correctly just for that one.
# So we shouldn't autouse everywhere, or we should override in that test.
# Actually, the user asked to do exactly this: patch these with sentinels that FAIL if called. Let's just do it directly in the tests that shouldn't hit it.

# I'll just write a whole new clean test file that does exactly what the user asked.
