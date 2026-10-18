with open("tests/test_a2a_argus_supervisor.py", "r") as f:
    content = f.read()

# Make sure tests import fasta2a server so patching works
content = content.replace("def guard_agent_zero_initialization():", "def guard_agent_zero_initialization():\n    import helpers.fasta2a_server\n")

with open("tests/test_a2a_argus_supervisor.py", "w") as f:
    f.write(content)
